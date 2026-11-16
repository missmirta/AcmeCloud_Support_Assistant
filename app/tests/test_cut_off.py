"""A reply cut off at the output limit is never used: the case goes to a human."""

import asyncio

import httpx
import pytest

from assistant import _HAND_OFF, Assistant
from llm import LLMClient, LLMCutOff
from test_assistant_flow import FakeMCP
from tracing import TraceRecorder


def test_length_finish_is_a_cut_off_even_when_some_text_was_written():
    body = {"choices": [{"message": {"role": "assistant", "content": "partial"}, "finish_reason": "length"}],
            "usage": {"total_tokens": 8192}}
    http = httpx.AsyncClient(base_url="http://llm",
                             transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
    with pytest.raises(LLMCutOff) as info:
        asyncio.run(LLMClient(http).chat([{"role": "user", "content": "q"}]))
    assert info.value.tokens == 8192  # the spent tokens reach the trace


def test_hand_off_opens_a_ticket_and_gives_no_automatic_answer():
    mcp = FakeMCP()
    trace = TraceRecorder("req_cut", "Can you check my invoice?", "cust_001")
    answer, sources = asyncio.run(Assistant(None, None, mcp).hand_off(trace))
    assert answer == _HAND_OFF and sources == []
    assert [tool for tool, _ in mcp.calls] == ["escalate_to_human"]
