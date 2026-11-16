"""
MCP Server for AcmeCloud Support Assistant.
Provides tool interface to backend services.
"""

import json
import os
from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel

from tools import (
    ToolError,
    get_account_status_impl,
    get_billing_history_impl,
    escalate_to_human_impl,
    get_payment_method_impl,
    check_usage_impl,
)

app = FastAPI(title="AcmeCloud MCP Server")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")


class MCPRequest(BaseModel):
    method: str
    params: Dict[str, Any]


class MCPResponse(BaseModel):
    content: List[Dict[str, Any]]
    isError: bool = False


TOOLS = {
    "get_account_status": lambda p: get_account_status_impl(p.get("customer_id"), BACKEND_URL),
    "get_billing_history": lambda p: get_billing_history_impl(p.get("customer_id"), BACKEND_URL),
    "escalate_to_human": lambda p: escalate_to_human_impl(
        customer_id=p.get("customer_id"),
        issue=p.get("issue"),
        priority=p.get("priority", "P3"),
        backend_url=BACKEND_URL,
        idempotency_key=p.get("idempotency_key"),
    ),
    "get_payment_method": lambda p: get_payment_method_impl(p.get("payment_method_id"), BACKEND_URL),
    "check_usage": lambda p: check_usage_impl(p.get("customer_id"), BACKEND_URL),
}


def _response(payload: Dict[str, Any], is_error: bool = False) -> MCPResponse:
    """Tool output is always a JSON document in a single text content block."""
    return MCPResponse(content=[{"type": "text", "text": json.dumps(payload)}], isError=is_error)


@app.get("/health")
def health():
    return {"status": "ok", "backend_url": BACKEND_URL}


@app.post("/mcp")
def mcp_endpoint(request: MCPRequest):
    """
    MCP endpoint for tool calls.

    Success: the backend payload as JSON (including as_of / ticket_id).
    Failure: isError=true and {"error": {"type", "message", "retry_after"?}}
    where type is one of rate_limit, timeout, service_error, not_found,
    invalid_params, unknown_method - so the caller can choose how to react.
    """
    tool = TOOLS.get(request.method)
    if tool is None:
        error = ToolError("unknown_method", f"Unknown method: {request.method}")
        return _response(error.to_dict(), is_error=True)

    try:
        return _response(tool(request.params))
    except ToolError as e:
        return _response(e.to_dict(), is_error=True)
    except Exception as e:
        error = ToolError("service_error", f"Unexpected error: {type(e).__name__}")
        return _response(error.to_dict(), is_error=True)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MCP_PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
