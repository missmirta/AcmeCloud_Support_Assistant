"""Per-request trace recording and an in-memory trace store."""

import time
from collections import OrderedDict
from typing import Any, Optional

from models import Trace, TraceEntry

_MAX_TRACES = 1000


class TraceRecorder:
    """Timeline of one request. Counters are derived from it, never tracked separately."""

    def __init__(self, request_id: str, question: str, customer_id: str):
        self.request_id = request_id
        self.question = question
        self.customer_id = customer_id
        self.timeline: list[TraceEntry] = []

    def add(self, type: str, **details: Any) -> None:
        self.timeline.append(TraceEntry(timestamp=time.time(), type=type, details=details))

    def _count(self, type: str) -> int:
        return sum(1 for entry in self.timeline if entry.type == type)

    @property
    def llm_calls(self) -> int:
        return self._count("llm_call")

    @property
    def tool_calls(self) -> int:
        return self._count("tool_call")

    @property
    def retries(self) -> int:
        return sum(e.details.get("retry_count", 0) for e in self.timeline if e.type == "tool_call")

    def to_trace(self) -> Trace:
        return Trace(
            request_id=self.request_id,
            question=self.question,
            customer_id=self.customer_id,
            timeline=list(self.timeline),
            total_llm_calls=self.llm_calls,
            total_tool_calls=self.tool_calls,
            total_retries=self.retries,
        )


class TraceStore:
    """Bounded in-memory store; the oldest traces are evicted first."""

    def __init__(self, max_traces: int = _MAX_TRACES):
        self._traces: "OrderedDict[str, Trace]" = OrderedDict()
        self._max = max_traces

    def put(self, trace: Trace) -> None:
        self._traces[trace.request_id] = trace
        self._traces.move_to_end(trace.request_id)
        while len(self._traces) > self._max:
            self._traces.popitem(last=False)

    def get(self, request_id: str) -> Optional[Trace]:
        return self._traces.get(request_id)
