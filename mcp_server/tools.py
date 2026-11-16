"""
Tool implementations for MCP server.

Each tool makes exactly one backend attempt and reports precisely what
happened. Retry policy belongs to the caller (the app), which is the only
place that can count retries and bound total latency for a request.
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

# The backend either answers immediately or hangs for 5-30s before a 504,
# so waiting longer than this only delays the caller's retry.
REQUEST_TIMEOUT = 4


class ToolError(Exception):
    """A tool failure the caller can act on (retry, wait, or give up)."""

    def __init__(self, type: str, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.type = type
        self.message = message
        self.retry_after = retry_after

    def to_dict(self) -> Dict[str, Any]:
        error: Dict[str, Any] = {"type": self.type, "message": self.message}
        if self.retry_after is not None:
            error["retry_after"] = self.retry_after
        return {"error": error}


def _require(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolError("invalid_params", f"{name} is required")
    return value


def _call_backend(method: str, url: str, **kwargs) -> Dict[str, Any]:
    """Single backend attempt. Returns the JSON payload or raises ToolError."""
    try:
        response = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.exceptions.Timeout:
        raise ToolError("timeout", f"Backend did not respond within {REQUEST_TIMEOUT}s")
    except requests.exceptions.RequestException as e:
        raise ToolError("service_error", f"Backend unreachable: {type(e).__name__}")

    if response.status_code == 200:
        return response.json()
    if response.status_code == 429:
        try:
            retry_after = float(response.headers.get("Retry-After", 1))
        except ValueError:
            retry_after = 1.0
        raise ToolError("rate_limit", "Backend rate limit exceeded", retry_after=retry_after)
    if response.status_code == 404:
        raise ToolError("not_found", "Resource not found")
    if response.status_code == 504:
        raise ToolError("timeout", "Backend gateway timeout")
    raise ToolError("service_error", f"Backend returned HTTP {response.status_code}")


def get_account_status_impl(customer_id: str, backend_url: str) -> Dict[str, Any]:
    """Get customer account status, including as_of and canceled/suspended dates."""
    customer_id = _require(customer_id, "customer_id")
    return _call_backend("GET", f"{backend_url}/account/{quote(customer_id, safe='')}")


def get_billing_history_impl(customer_id: str, backend_url: str) -> Dict[str, Any]:
    """Get customer billing history, including the as_of freshness timestamp."""
    customer_id = _require(customer_id, "customer_id")
    data = _call_backend("GET", f"{backend_url}/billing/{quote(customer_id, safe='')}")
    return {"customer_id": customer_id, **data}


def escalate_to_human_impl(
    customer_id: str,
    issue: str,
    priority: str,
    backend_url: str,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a support ticket and return its ticket_id.

    The idempotency key must be identical across retries of the same
    escalation, so that a retry after a timeout cannot create a duplicate.
    Callers should supply one; the fallback is derived from the ticket content.
    """
    customer_id = _require(customer_id, "customer_id")
    issue = _require(issue, "issue")
    if not idempotency_key:
        idempotency_key = hashlib.sha256(
            f"{customer_id}|{issue}|{priority}".encode()
        ).hexdigest()

    return _call_backend(
        "POST",
        f"{backend_url}/tickets",
        json={"customer_id": customer_id, "issue": issue, "priority": priority},
        headers={"Idempotency-Key": idempotency_key},
    )


def get_payment_method_impl(payment_method_id: str, backend_url: str) -> Dict[str, Any]:
    """
    Get payment method details.

    payment_method_id must be obtained from get_account_status first.
    """
    payment_method_id = _require(payment_method_id, "payment_method_id")
    data = _call_backend(
        "GET", f"{backend_url}/payment-method/{quote(payment_method_id, safe='')}"
    )

    is_expired = False
    if data.get("type") == "card":
        now = datetime.now()
        # A card is valid through the end of its expiration month.
        expiry = (data.get("exp_year", 0), data.get("exp_month", 0))
        is_expired = expiry < (now.year, now.month)

    return {"payment_method_id": payment_method_id, **data, "is_expired": is_expired}


def check_usage_impl(customer_id: str, backend_url: str) -> Dict[str, Any]:
    """Get API usage statistics for customer."""
    customer_id = _require(customer_id, "customer_id")
    return _call_backend("GET", f"{backend_url}/usage/{quote(customer_id, safe='')}")
