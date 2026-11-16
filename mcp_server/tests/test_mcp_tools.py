"""MCP server: payload passthrough, error typing, idempotency."""

import json

import pytest
import requests

import server
import tools


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self):
        return self._payload


@pytest.fixture
def backend(monkeypatch):
    """Replace the HTTP call; records requests and replays queued responses."""
    calls, queue = [], []

    def fake_request(method, url, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(tools.requests, "request", fake_request)
    return calls, queue






@pytest.mark.parametrize(
    "response, expected_type",
    [
        (FakeResponse(429, headers={"Retry-After": "5"}), "rate_limit"),
        (FakeResponse(503), "service_error"),
        (FakeResponse(504), "timeout"),
        (FakeResponse(404), "not_found"),
        (requests.exceptions.Timeout(), "timeout"),
        (requests.exceptions.ConnectionError(), "service_error"),
    ],
)
def test_backend_failures_are_typed(backend, response, expected_type):
    _, queue = backend
    queue.append(response)

    with pytest.raises(tools.ToolError) as raised:
        tools.get_account_status_impl("cust_001", "http://b")

    assert raised.value.type == expected_type






def test_customer_id_cannot_alter_backend_path(backend):
    calls, queue = backend
    queue.append(FakeResponse(payload={}))
    tools.get_account_status_impl("../audit/clear", "http://b")
    assert calls[0]["url"] == "http://b/account/..%2Faudit%2Fclear"


def test_escalation_returns_ticket_id_and_forwards_callers_key(backend):
    calls, queue = backend
    queue.append(FakeResponse(payload={"ticket_id": "TKT-1", "status": "created"}))

    result = tools.escalate_to_human_impl("cust_005", "refund", "P2", "http://b", idempotency_key="key-1")

    assert result["ticket_id"] == "TKT-1"
    assert calls[0]["headers"] == {"Idempotency-Key": "key-1"}




