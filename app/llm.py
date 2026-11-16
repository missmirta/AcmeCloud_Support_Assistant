"""
Client for an OpenAI-compatible chat + embeddings API (NVIDIA NIM by default).

Plain httpx against the two REST endpoints we use; no SDK needed.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
import numpy as np

import config

_EMBED_BATCH = 32
# Reasoning models spend output tokens on hidden reasoning before the answer;
# a small limit ends the reply (finish_reason "length") with no answer at all.
_MAX_OUTPUT_TOKENS = 8192


class LLMError(Exception):
    """The LLM provider failed or returned something unusable."""


class LLMCutOff(LLMError):
    """The reply hit the output limit before producing an answer or a function call."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON string as produced by the model


@dataclass
class LLMReply:
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    tokens: int = 0
    finish_reason: str = ""

    def as_message(self) -> Dict[str, Any]:
        """This reply as an assistant message for the follow-up call."""
        message: Dict[str, Any] = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            message["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                for c in self.tool_calls
            ]
        return message


class LLMClient:
    def __init__(self, http: Optional[httpx.AsyncClient] = None):
        self.chat_model = config.CHAT_MODEL
        self._http = http or httpx.AsyncClient(
            base_url=config.LLM_BASE_URL,
            headers={"Authorization": f"Bearer {config.NVIDIA_API_KEY}"},
            timeout=httpx.Timeout(90.0, connect=10.0),
        )

    async def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = await self._http.post(path, json=body)
        except httpx.HTTPError as e:
            raise LLMError(f"LLM provider unreachable: {type(e).__name__}") from e
        if response.status_code != 200:
            raise LLMError(f"LLM provider returned HTTP {response.status_code}: {response.text[:200]}")
        return response.json()

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,  # "none", "auto" or a forced-function object
    ) -> LLMReply:
        body: Dict[str, Any] = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": _MAX_OUTPUT_TOKENS,
        }
        if tools:
            body["tools"] = tools
        if tool_choice:
            body["tool_choice"] = tool_choice

        data = await self._post("/chat/completions", body)
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError("LLM provider returned no choices") from e

        tool_calls = [
            ToolCall(
                id=call.get("id") or f"call_{i}",
                name=call["function"]["name"],
                arguments=call["function"].get("arguments") or "{}",
            )
            for i, call in enumerate(message.get("tool_calls") or [])
        ]
        tokens = (data.get("usage") or {}).get("total_tokens", 0)
        content = (message.get("content") or "").strip()
        finish_reason = data["choices"][0].get("finish_reason") or ""
        if finish_reason == "length" and not content and not tool_calls:
            # Hit the output limit before any answer: fail loudly instead of
            # returning an empty reply that the caller would show as the answer.
            raise LLMCutOff(
                f"LLM reply cut off at {_MAX_OUTPUT_TOKENS} tokens with no answer "
                "(reasoning used the whole output budget)"
            )
        return LLMReply(
            content=content,
            tool_calls=tool_calls,
            tokens=tokens,
            finish_reason=finish_reason,
        )

    async def embed(self, texts: List[str], input_type: str) -> np.ndarray:
        vectors: List[List[float]] = []
        for start in range(0, len(texts), _EMBED_BATCH):
            data = await self._post(
                "/embeddings",
                {
                    "model": config.EMBED_MODEL,
                    "input": texts[start:start + _EMBED_BATCH],
                    "input_type": input_type,  # NIM retrieval models embed queries and passages differently
                    "truncate": "END",
                },
            )
            rows = sorted(data["data"], key=lambda row: row["index"])
            vectors.extend(row["embedding"] for row in rows)
        return np.asarray(vectors, dtype=np.float32)

    async def aclose(self) -> None:
        await self._http.aclose()
