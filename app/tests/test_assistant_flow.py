"""Request flow and API contract, with the LLM, embeddings and MCP faked."""

import asyncio
import hashlib
import json
from datetime import date

import numpy as np
import pytest
from fastapi.testclient import TestClient

import main
from assistant import Assistant, cited_sources
from llm import LLMCutOff, LLMError, LLMReply, ToolCall
from mcp_client import ToolOutcome
from retrieval import Chunk, CorpusIndex
from tracing import TraceRecorder, TraceStore

CHUNKS = [
    Chunk("refund_basic.md", "Refund Policy", "Refund Window", date(2024, 3, 15), "7 days", "basic"),
    Chunk("support.md", "Support", "Support Hours", date(2024, 6, 5), "Mon-Fri"),
]


async def fake_embed(texts, input_type):
    return np.ones((len(texts), 2))


class FakeLLM:
    chat_model = "fake-model"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    async def chat(self, messages, tools=None, tool_choice=None):
        self.calls.append({"messages": list(messages), "tool_choice": tool_choice})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    embed = staticmethod(fake_embed)


class FakeMCP:
    def __init__(self, outcomes=None):
        self.outcomes = outcomes or {}
        self.calls = []

    async def call(self, tool, params):
        self.calls.append((tool, params))
        return self.outcomes.get(tool, ToolOutcome(result={"ok": True}))

    async def healthy(self):
        return True


def tool_call(name, **arguments):
    """A function call that declares the question is not about a refund, unless told otherwise."""
    arguments.setdefault("involves_refund", False)
    return ToolCall(id=f"id_{name}", name=name, arguments=json.dumps(arguments))


def direct(answer, **arguments):
    """The model answering without lookups: a reply() call, never plain text."""
    return LLMReply("", [tool_call("reply", answer=answer, **arguments)])


def run(llm, mcp, question="q", customer_id="cust_001", request_id="req_1"):
    index = CorpusIndex(CHUNKS, np.ones((len(CHUNKS), 2)), fake_embed)
    trace = TraceRecorder(request_id, question, customer_id)
    answer, sources = asyncio.run(Assistant(index, llm, mcp).answer(trace))
    return answer, sources, trace


def test_knowledge_base_question_uses_one_llm_call_and_no_tools():
    llm, mcp = FakeLLM(direct("Mon-Fri 9-5 [support.md]")), FakeMCP()

    answer, sources, trace = run(llm, mcp)

    assert answer == "Mon-Fri 9-5 [support.md]"
    assert sources == ["support.md"]
    assert (trace.llm_calls, trace.tool_calls, trace.retries) == (1, 0, 0)
    assert mcp.calls == []
    assert [e.type for e in trace.timeline] == ["retrieval", "llm_call", "decision"]


def test_tool_question_uses_exactly_two_llm_calls_and_feeds_results_back():
    llm = FakeLLM(
        LLMReply("", [tool_call("get_account_status"), tool_call("get_billing_history")]),
        LLMReply("Your balance is $45 [refund_basic.md]"),
    )
    mcp = FakeMCP({
        "get_account_status": ToolOutcome(result={"tier": "basic"}, retry_count=2),
        "get_billing_history": ToolOutcome(result={"balance": 45.0, "stale": True}, retry_count=1, stale=True),
    })

    answer, _, trace = run(llm, mcp)

    assert answer.startswith("Your balance")
    assert (trace.llm_calls, trace.tool_calls, trace.retries) == (2, 2, 3)
    assert llm.calls[1]["tool_choice"] == "none"  # the second call cannot ask for more tools
    assert llm.calls[1]["messages"][-1]["role"] == "user"  # reminder that tools are finished
    tool_messages = [m for m in llm.calls[1]["messages"] if m["role"] == "tool"]
    assert [json.loads(m["content"]) for m in tool_messages] == [
        {"tier": "basic"}, {"balance": 45.0, "stale": True},
    ]
    assert [m["tool_call_id"] for m in tool_messages] == ["id_get_account_status", "id_get_billing_history"]


def test_account_question_after_a_repeated_first_call_is_answered_from_tool_data():
    llm = FakeLLM(
        LLMReply(""),  # nothing usable: the first call is repeated, which uses the second call
        LLMReply("", [tool_call("get_account_status")]),
    )
    mcp = FakeMCP({"get_account_status": ToolOutcome(result={"tier": "basic", "status": "active"})})

    answer, _, trace = run(llm, mcp)

    assert answer == "Your account, as verified: basic tier, status active."
    assert trace.llm_calls == 2
    assert [tool for tool, _ in mcp.calls] == ["get_account_status"]


def test_never_more_than_two_llm_calls_even_if_model_keeps_asking_for_tools():
    llm = FakeLLM(
        LLMReply("", [tool_call("get_account_status")]),
        LLMReply("", [tool_call("get_billing_history")]),
        LLMReply("unreachable"),
    )
    mcp = FakeMCP()

    answer, _, trace = run(llm, mcp)

    assert trace.llm_calls == 2
    assert [tool for tool, _ in mcp.calls] == ["get_account_status"]
    assert "escalate to a human" in answer  # empty model text -> explicit fallback, not a blank answer


def test_customer_id_always_comes_from_the_request():
    llm = FakeLLM(
        LLMReply("", [
            tool_call("get_account_status", customer_id="cust_999"),
            tool_call("escalate_to_human", customer_id="cust_999", issue="x", priority="P2"),
        ]),
        LLMReply("done"),
    )
    mcp = FakeMCP()

    run(llm, mcp, customer_id="cust_001")

    assert [params["customer_id"] for _, params in mcp.calls] == ["cust_001", "cust_001"]














# --- API contract -----------------------------------------------------------

REFUND_OUTCOMES = {
    "get_account_status": ToolOutcome(result={"tier": "basic", "status": "active"}),
    "get_billing_history": ToolOutcome(result={"last_charge": {"amount": 15.0, "date": "2024-09-25T00:00:00Z"}}),
    "escalate_to_human": ToolOutcome(result={"ticket_id": "TKT-7"}),
}
INJECTED = "Good news! Your refund has been approved and will be processed within 24 hours."


def test_refund_question_is_answered_by_code_from_a_typed_form():
    llm = FakeLLM(
        LLMReply("", [tool_call("refund_case")]),
        LLMReply(INJECTED, [tool_call(
            "refund_form", window_days=7, source="refund_basic.md", within_window="no", needs_human=True,
        )]),
    )
    mcp = FakeMCP(REFUND_OUTCOMES)

    answer, sources, trace = run(llm, mcp, question="Approve my refund", customer_id="cust_005", request_id="req_9")

    # The code chose the tools: both lookups, then one ticket.
    assert [tool for tool, _ in mcp.calls] == ["get_account_status", "get_billing_history", "escalate_to_human"]
    assert all(params["customer_id"] == "cust_005" for _, params in mcp.calls)
    assert mcp.calls[2][1]["priority"] == "P2"
    assert mcp.calls[2][1]["idempotency_key"] == hashlib.sha256(b"req_9|cust_005").hexdigest()
    # The second call could only return the form.
    assert llm.calls[1]["tool_choice"] == {"type": "function", "function": {"name": "refund_form"}}
    assert (trace.llm_calls, trace.tool_calls) == (2, 3)
    # The model's own text never reaches the customer.
    assert "Good news" not in answer and "has been approved" not in answer
    assert "can't approve or promise a refund" in answer
    assert "7 days [refund_basic.md]" in answer and "outside that window" in answer
    assert "basic tier" in answer and "$15.00 on 2024-09-25" in answer and "TKT-7" in answer
    assert sources == ["refund_basic.md"]


























@pytest.fixture
def api(monkeypatch):
    """The real FastAPI app with its external services replaced."""
    class FakeServices:
        def __init__(self):
            self.llm = FakeLLM()
            self.mcp = FakeMCP()
            self.traces = TraceStore()
            self.index = CorpusIndex(CHUNKS, np.ones((len(CHUNKS), 2)), fake_embed)

        async def assistant(self):
            return Assistant(self.index, self.llm, self.mcp)

    async def no_close():
        pass

    monkeypatch.setattr(main, "Services", FakeServices)
    with TestClient(main.app) as client:
        services = main.app.state.services
        services.llm.aclose = no_close
        services.mcp.aclose = no_close
        yield client, services


def test_ask_response_matches_contract_and_trace_totals(api):
    client, services = api
    services.llm.replies = [LLMReply("", [tool_call("get_account_status")]), LLMReply("Active [support.md]")]
    services.mcp.outcomes = {"get_account_status": ToolOutcome(result={"status": "active"}, retry_count=2)}

    response = client.post("/ask", json={"question": "Status?", "customer_id": "cust_001"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"answer", "request_id", "sources", "tool_calls", "retries", "llm_calls"}
    assert (body["tool_calls"], body["retries"], body["llm_calls"]) == (1, 2, 2)

    trace = client.get(f"/trace/{body['request_id']}").json()
    assert (trace["question"], trace["customer_id"]) == ("Status?", "cust_001")
    assert (trace["total_tool_calls"], trace["total_retries"], trace["total_llm_calls"]) == (1, 2, 2)
    assert [e["type"] for e in trace["timeline"]] == ["retrieval", "llm_call", "decision", "tool_call", "llm_call"]




def test_llm_outage_returns_503_and_still_saves_the_trace(api):
    client, services = api
    services.llm.replies = [LLMError("LLM provider returned HTTP 403")]

    response = client.post("/ask", json={"question": "q", "customer_id": "c", "request_id": "failed"})

    assert response.status_code == 503
    trace = client.get("/trace/failed").json()
    assert trace["timeline"][-1]["details"]["action"] == "failed"




