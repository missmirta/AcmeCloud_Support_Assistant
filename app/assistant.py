"""
Request flow: retrieve -> LLM call 1 -> (tools -> LLM call 2).

Refund questions take a separate path (see refund.py): the model only fills in
a typed form and the answer text is written by code.

The LLM budget is enforced by structure: there is no loop, so a request can
never make more than two LLM calls.
"""

import asyncio
import hashlib
import json
import re
from dataclasses import asdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from llm import LLMClient, LLMCutOff, LLMReply, ToolCall
from mcp_client import MCPClient, ToolOutcome
from prompts import (
    FINAL_ANSWER_REMINDER, REFUND_CASE, REFUND_FLAG, REPLY, SYSTEM_PROMPT, TOOLS, build_user_prompt, tools_for,
)
from refund import (
    FORM_INSTRUCTION, FORM_NAME, Excerpt, days_since_last_charge, form_schema, parse_form, render_answer,
    render_lookup_answer,
)
from retrieval import Chunk, CorpusIndex
from tracing import TraceRecorder

TOP_K = 8
MAX_LLM_CALLS = 2
_MAX_ISSUE_CHARS = 1000
_PRIORITIES = {"P1", "P2", "P3"}
# Tools executed through MCP. refund_case and reply are not MCP tools: one is a
# routing signal, the other carries a direct answer.
_KNOWN_TOOLS = {tool["function"]["name"] for tool in TOOLS} - {REFUND_CASE, REPLY}
_CITATION_RE = re.compile(r"[\w\-]+\.md")
# Tool-call markup emitted as text means the model tried to call a tool where it
# could not; that is not an answer and must not be shown to a customer.
_TOOL_MARKUP_RE = re.compile(r"</?tool_call\b|<function=", re.IGNORECASE)
_NO_ANSWER = "I wasn't able to produce an answer for this question. Please escalate to a human agent."
_HAND_OFF = "I can't answer this automatically. A human agent will review your request."


def _parse_arguments(raw: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _is_refund_case(calls: List[ToolCall]) -> bool:
    """
    True unless every call explicitly declares that the question does not
    involve a refund. A missing or malformed flag counts as a refund question:
    the model's own text is shown only after an explicit "false".
    """
    return any(
        call.name == REFUND_CASE or _parse_arguments(call.arguments).get(REFUND_FLAG) not in (False, "false")
        for call in calls
    )


def cited_sources(answer: str, hits: List[Tuple[Chunk, float]]) -> List[str]:
    """Retrieved files the answer cites. None cited means none used (e.g. a tool-only answer)."""
    retrieved = {chunk.source for chunk, _ in hits}
    return [name for name in dict.fromkeys(_CITATION_RE.findall(answer)) if name in retrieved]


def _declared_sources(args: Dict[str, Any], hits: List[Tuple[Chunk, float]]) -> List[str]:
    """Files the model declared in reply(), limited to the retrieved ones (model output is untrusted)."""
    retrieved = {chunk.source for chunk, _ in hits}
    declared = args.get("sources")
    if not isinstance(declared, list):
        return []
    return [name for name in dict.fromkeys(n for n in declared if isinstance(n, str)) if name in retrieved]


class Assistant:
    def __init__(self, index: CorpusIndex, llm: LLMClient, mcp: MCPClient):
        self._index = index
        self._llm = llm
        self._mcp = mcp

    def _tool_params(self, call: ToolCall, trace: TraceRecorder) -> Dict[str, Any]:
        """
        MCP params for a model-requested call. customer_id always comes from
        the request; model-supplied arguments are used only for the ticket text.
        """
        params: Dict[str, Any] = {"customer_id": trace.customer_id}
        if call.name == "escalate_to_human":
            args = _parse_arguments(call.arguments)
            issue = str(args.get("issue") or "").strip() or trace.question
            priority = args.get("priority")
            params["issue"] = issue[:_MAX_ISSUE_CHARS]
            params["priority"] = priority if priority in _PRIORITIES else "P3"
            # One key per request: retries (ours or the client re-sending the
            # same request_id) can never open a second ticket.
            params["idempotency_key"] = hashlib.sha256(
                f"{trace.request_id}|{trace.customer_id}".encode()
            ).hexdigest()
        return params

    async def _run_tools(
        self, calls: List[ToolCall], trace: TraceRecorder, outcomes_out: Optional[Dict[str, ToolOutcome]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute the requested tools concurrently; returns tool messages in call
        order. If outcomes_out is given it receives each tool's outcome by name.
        """
        runnable: Dict[int, Dict[str, Any]] = {}
        seen = set()
        for i, call in enumerate(calls):
            # Each tool takes no model-chosen input that changes its result,
            # so a repeated call in the same turn is redundant.
            if call.name in _KNOWN_TOOLS and call.name not in seen:
                seen.add(call.name)
                runnable[i] = self._tool_params(call, trace)

        outcomes = await asyncio.gather(*(self._mcp.call(calls[i].name, p) for i, p in runnable.items()))
        by_index = dict(zip(runnable, outcomes))

        messages = []
        for i, call in enumerate(calls):
            if i in by_index:
                outcome: ToolOutcome = by_index[i]
                if outcomes_out is not None:
                    outcomes_out[call.name] = outcome
                trace.add(
                    "tool_call",
                    tool=call.name,
                    params=runnable[i],
                    result=outcome.result,
                    error=outcome.error,
                    retry_count=outcome.retry_count,
                    stale=outcome.stale,
                    attempts=outcome.attempts,
                )
                content = outcome.for_llm()
            else:
                reason = "duplicate call ignored" if call.name in _KNOWN_TOOLS else "unknown tool"
                trace.add("decision", action="tool_call_skipped", tool=call.name, reason=reason)
                content = {"error": {"type": "invalid_call", "message": reason}}
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(content)})
        return messages

    async def answer(self, trace: TraceRecorder) -> Tuple[str, List[str]]:
        """Answer trace.question, recording every step. Returns (answer, sources)."""
        hits = await self._index.search(trace.question, TOP_K)
        trace.add(
            "retrieval",
            query=trace.question,
            chunks=[
                {
                    "source": chunk.source,
                    "section": chunk.section,
                    "doc_date": chunk.doc_date.isoformat() if chunk.doc_date else None,
                    "content": chunk.text,
                    "score": round(score, 4),
                }
                for chunk, score in hits
            ],
        )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(trace.question, trace.customer_id, hits, date.today())},
        ]
        tools = tools_for(list(dict.fromkeys(chunk.source for chunk, _ in hits)))

        reply = await self._first_call(messages, tools, trace)
        if reply is None:
            trace.add("decision", action="fallback_answer", reason="model returned no function call twice")
            return _NO_ANSWER, []
        llm_call_left = trace.llm_calls < MAX_LLM_CALLS

        if _is_refund_case(reply.tool_calls):
            return await self._answer_refund_case(messages, hits, trace, llm_call_left)

        lookups = [call for call in reply.tool_calls if call.name != REPLY]
        if lookups and not llm_call_left:
            # The repeated first call used the second call: the code writes the answer from tool data.
            trace.add("decision", action="answer_from_tool_data",
                      reason="first call had to be repeated; no LLM call left to write the answer",
                      tools=[c.name for c in lookups])
            outcomes: Dict[str, ToolOutcome] = {}
            await self._run_tools(lookups, trace, outcomes)
            return render_lookup_answer(outcomes) or _NO_ANSWER, []
        if lookups:
            trace.add("decision", action="call_tools", tools=[c.name for c in lookups])
            messages.append(LLMReply(reply.content, lookups).as_message())
            messages.extend(await self._run_tools(lookups, trace))
            messages.append({"role": "user", "content": FINAL_ANSWER_REMINDER})
            reply = await self._llm.chat(messages, tools=tools, tool_choice="none")
            trace.add("llm_call", model=self._llm.chat_model, tokens=reply.tokens,
                      finish_reason=reply.finish_reason, purpose="synthesize_answer")
            answer = reply.content
            sources = cited_sources(answer, hits) if answer else []
        else:
            trace.add("decision", action="answer_from_knowledge_base")
            args = _parse_arguments(reply.tool_calls[0].arguments)
            answer = str(args.get("answer") or "").strip()
            sources = _declared_sources(args, hits)

        if not answer or _TOOL_MARKUP_RE.search(answer):
            trace.add("decision", action="fallback_answer", reason="model returned no usable text", raw=answer)
            return _NO_ANSWER, []
        return answer, sources

    async def hand_off(self, trace: TraceRecorder) -> Tuple[str, List[str]]:
        """An LLM reply hit the output limit: open a human ticket and give no automatic answer."""
        trace.add("decision", action="hand_off", reason="LLM reply cut off at the output limit")
        ticket = ToolCall("open_ticket", "escalate_to_human", json.dumps(
            {"issue": f"Request not answered automatically (reply cut off). Customer wrote: {trace.question}",
             "priority": "P2"}
        ))
        await self._run_tools([ticket], trace)
        return _HAND_OFF, []

    async def _first_call(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], trace: TraceRecorder
    ) -> Optional[LLMReply]:
        """
        The first LLM call, which must return a function call. "required" means
        the response always carries the refund flag; text without a function
        call carries no declaration and is never shown. The model sometimes
        returns nothing, or spends its whole output budget reasoning: that is
        retried once, which uses up the second LLM call.
        """
        for _ in range(MAX_LLM_CALLS):
            reply = await self._llm.chat(messages, tools=tools, tool_choice="required")
            trace.add("llm_call", model=self._llm.chat_model, tokens=reply.tokens,
                      finish_reason=reply.finish_reason, purpose="answer_or_select_tools")
            if reply.tool_calls:
                return reply
            trace.add("decision", action="retry_first_call",
                      reason="model returned no function call", raw=reply.content)
        return None

    async def _answer_refund_case(
        self, messages: List[Dict[str, Any]], hits: List[Tuple[Chunk, float]], trace: TraceRecorder,
        llm_call_left: bool = True,
    ) -> Tuple[str, List[str]]:
        """
        Refund path. The code, not the model, decides which tools run and writes
        the answer; the model's second call can only return the typed form.
        """
        trace.add("decision", action="refund_case",
                  reason="refund question: lookups and answer text are handled by code")
        lookups = [ToolCall("lookup_account", "get_account_status", "{}"),
                   ToolCall("lookup_billing", "get_billing_history", "{}")]
        outcomes: Dict[str, ToolOutcome] = {}
        messages.append(LLMReply("", lookups).as_message())
        messages.extend(await self._run_tools(lookups, trace, outcomes))
        messages.append({"role": "user", "content": FORM_INSTRUCTION})

        excerpts: Dict[str, Excerpt] = {}
        for chunk, _ in hits:
            text = excerpts[chunk.source].text + "\n" + chunk.text if chunk.source in excerpts else chunk.text
            excerpts[chunk.source] = Excerpt(text, chunk.tier)
        account_tier = (outcomes["get_account_status"].result or {}).get("tier")
        # Without a form the answer is still written, from tool data alone, and a human gets the case.
        raw, discarded = None, None
        if llm_call_left:
            reply = await self._llm.chat(
                messages,
                tools=[form_schema(list(excerpts))],
                tool_choice={"type": "function", "function": {"name": FORM_NAME}},
            )
            trace.add("llm_call", model=self._llm.chat_model, tokens=reply.tokens,
                      finish_reason=reply.finish_reason, purpose="fill_refund_form")
            # Any text the model wrote here is discarded: only the form is read.
            raw = next((_parse_arguments(c.arguments) for c in reply.tool_calls if c.name == FORM_NAME), None)
            discarded = reply.content or None
        form = parse_form(raw or {}, excerpts, account_tier,
                          days_since_last_charge(outcomes["get_billing_history"], date.today()))
        trace.add("decision", action="refund_form", returned=raw, used=asdict(form), discarded_text=discarded)

        # Any problem in the lookups or the form sends the case to a human, not just the form's own flag.
        lookups_failed = any(not outcomes[k].result for k in ("get_account_status", "get_billing_history"))
        if form.needs_human or lookups_failed:
            ticket = ToolCall("open_ticket", "escalate_to_human", json.dumps(
                {"issue": f"Refund request to review. Customer wrote: {trace.question}", "priority": "P2"}
            ))
            await self._run_tools([ticket], trace, outcomes)

        answer = render_answer(
            form, outcomes["get_account_status"], outcomes["get_billing_history"], outcomes.get("escalate_to_human")
        )
        return answer, form.sources
