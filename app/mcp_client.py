"""
MCP client. Owns the retry policy for tool calls:

- rate_limit            -> wait the server's Retry-After, then retry
- timeout/service_error -> exponential backoff, then retry
- anything else         -> fail immediately (retrying cannot help)
- stale success         -> retry for a fresh copy; if none arrives, return the
                           freshest one flagged stale=True

Bounded by MAX_ATTEMPTS and a per-call deadline.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import httpx

MAX_ATTEMPTS = 4
DEADLINE_SECONDS = 25.0
BACKOFF_SECONDS = (0.5, 1.0, 2.0)
REQUEST_TIMEOUT = 6.0  # must exceed the MCP server's own 4s backend timeout
RETRYABLE = {"rate_limit", "timeout", "service_error"}
# corpus/account_and_billing.md: cached data "may be up to 24 hours old".
STALE_AFTER = timedelta(hours=24)


@dataclass
class ToolOutcome:
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    stale: bool = False
    attempts: List[Dict[str, Any]] = field(default_factory=list)

    def for_llm(self) -> Dict[str, Any]:
        """What the model sees: the data, or an explicit error."""
        return self.result if self.result is not None else {"error": self.error}


def _parse_as_of(data: Dict[str, Any]) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(data["as_of"])
    except (KeyError, TypeError, ValueError):
        return None


class MCPClient:
    def __init__(
        self,
        base_url: str,
        http: Optional[httpx.AsyncClient] = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        now: Callable[[], datetime] = datetime.now,
    ):
        self._http = http or httpx.AsyncClient(base_url=base_url, timeout=REQUEST_TIMEOUT)
        self._sleep = sleep
        self._now = now

    async def _attempt(self, tool: str, params: Dict[str, Any]) -> Tuple[Optional[Dict], Optional[Dict]]:
        """One MCP call. Returns (data, None) or (None, error)."""
        try:
            response = await self._http.post("/mcp", json={"method": tool, "params": params})
        except httpx.TimeoutException:
            return None, {"type": "timeout", "message": "MCP server did not respond"}
        except httpx.HTTPError as e:
            return None, {"type": "service_error", "message": f"MCP server unreachable: {type(e).__name__}"}
        if response.status_code != 200:
            return None, {"type": "service_error", "message": f"MCP server returned HTTP {response.status_code}"}

        try:
            body = response.json()
            payload = json.loads(body["content"][0]["text"])
            if not isinstance(payload, dict):
                raise ValueError("payload is not an object")
        except (ValueError, KeyError, IndexError, TypeError):
            return None, {"type": "service_error", "message": "Malformed MCP response"}

        if body.get("isError"):
            error = payload.get("error")
            if not isinstance(error, dict) or "type" not in error:
                error = {"type": "service_error", "message": "Unspecified tool error"}
            return None, error
        return payload, None

    def _is_stale(self, data: Dict[str, Any]) -> bool:
        as_of = _parse_as_of(data)
        if as_of is None:
            return False
        now = self._now().astimezone(as_of.tzinfo) if as_of.tzinfo else self._now()
        return now - as_of > STALE_AFTER

    async def call(self, tool: str, params: Dict[str, Any]) -> ToolOutcome:
        started = time.monotonic()
        attempts: List[Dict[str, Any]] = []
        freshest: Optional[Dict[str, Any]] = None
        error: Optional[Dict[str, Any]] = None

        for attempt in range(MAX_ATTEMPTS):
            data, error = await self._attempt(tool, params)
            delay = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]

            if error is None:
                if not self._is_stale(data):
                    attempts.append({"outcome": "ok"})
                    return ToolOutcome(result=data, retry_count=attempt, attempts=attempts)
                attempts.append({"outcome": "stale", "as_of": data.get("as_of")})
                if freshest is None or _parse_as_of(data) > _parse_as_of(freshest):
                    freshest = data
            else:
                attempts.append({"outcome": error["type"], "message": error.get("message")})
                if error["type"] not in RETRYABLE:
                    break
                if error["type"] == "rate_limit":
                    delay = float(error.get("retry_after") or delay)

            out_of_time = time.monotonic() - started + delay > DEADLINE_SECONDS
            if attempt == MAX_ATTEMPTS - 1 or out_of_time:
                break
            await self._sleep(delay)

        retry_count = len(attempts) - 1
        if freshest is not None:
            # Stale data beats no data, as long as it is labelled as such.
            return ToolOutcome(
                result={**freshest, "stale": True},
                retry_count=retry_count,
                stale=True,
                attempts=attempts,
            )
        return ToolOutcome(error=error, retry_count=retry_count, attempts=attempts)

    async def healthy(self) -> bool:
        try:
            response = await self._http.get("/health", timeout=2.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def aclose(self) -> None:
        await self._http.aclose()
