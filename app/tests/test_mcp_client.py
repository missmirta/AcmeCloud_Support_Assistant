"""MCP client retry policy: what is retried, how long it waits, what is reported."""

import asyncio
import json
from datetime import datetime, timedelta

import httpx

from mcp_client import MAX_ATTEMPTS, MCPClient

NOW = datetime(2026, 11, 15, 12, 0, 0)
FRESH = NOW.isoformat()
STALE = (NOW - timedelta(hours=30)).isoformat()
STALER = (NOW - timedelta(hours=60)).isoformat()


def ok(payload):
    return {"content": [{"type": "text", "text": json.dumps(payload)}], "isError": False}


def err(type, **extra):
    error = {"type": type, "message": type, **extra}
    return {"content": [{"type": "text", "text": json.dumps({"error": error})}], "isError": True}


def run_call(responses, tool="get_billing_history", params=None):
    """Replay `responses` (dicts or exceptions) and return (outcome, sleeps, requests)."""
    queue, sleeps, requests = list(responses), [], []

    def handler(request):
        requests.append(json.loads(request.content))
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return httpx.Response(200, json=item)

    async def sleep(seconds):
        sleeps.append(seconds)

    async def run():
        http = httpx.AsyncClient(base_url="http://mcp", transport=httpx.MockTransport(handler))
        client = MCPClient("http://mcp", http=http, sleep=sleep, now=lambda: NOW)
        return await client.call(tool, params or {"customer_id": "cust_003"})

    return asyncio.run(run()), sleeps, requests




def test_rate_limit_waits_for_retry_after():
    outcome, sleeps, _ = run_call([err("rate_limit", retry_after=5), ok({"as_of": FRESH})])

    assert outcome.result is not None
    assert outcome.retry_count == 1
    assert sleeps == [5.0]




def test_gives_up_after_max_attempts_and_reports_last_error():
    outcome, sleeps, requests = run_call([err("service_error")] * MAX_ATTEMPTS)

    assert outcome.result is None
    assert outcome.error["type"] == "service_error"
    assert outcome.retry_count == MAX_ATTEMPTS - 1
    assert len(requests) == MAX_ATTEMPTS
    assert outcome.for_llm() == {"error": outcome.error}




def test_stale_data_is_refetched_until_fresh():
    outcome, _, _ = run_call([ok({"balance": 1.0, "as_of": STALE}), ok({"balance": 2.0, "as_of": FRESH})])

    assert outcome.result == {"balance": 2.0, "as_of": FRESH}
    assert (outcome.retry_count, outcome.stale) == (1, False)






def test_retried_escalation_resends_identical_request_including_idempotency_key():
    params = {"customer_id": "cust_005", "issue": "refund", "priority": "P2", "idempotency_key": "k"}
    outcome, _, requests = run_call(
        [httpx.ReadTimeout("slow"), ok({"ticket_id": "TKT-1"})], tool="escalate_to_human", params=params
    )

    assert outcome.result["ticket_id"] == "TKT-1"
    assert requests[0] == requests[1]
    assert requests[0]["params"]["idempotency_key"] == "k"


