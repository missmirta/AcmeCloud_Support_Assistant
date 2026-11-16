"""
Pydantic models for API contract.
These define the exact API interface expected by the review process.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class AskRequest(BaseModel):
    """Request to ask a question."""
    question: str = Field(..., description="The customer's question")
    customer_id: str = Field(..., description="Customer ID for context")
    request_id: Optional[str] = Field(None, description="Optional request ID for trace lookup")


class AskResponse(BaseModel):
    """Response to a question."""
    answer: str = Field(..., description="The answer to the customer's question")
    request_id: str = Field(..., description="Request ID for trace lookup")
    sources: List[str] = Field(..., description="List of corpus document paths used")
    tool_calls: int = Field(..., description="Total number of tool calls made")
    retries: int = Field(..., description="Total number of retry attempts")
    llm_calls: int = Field(..., description="Total number of LLM calls made")


class TraceEntry(BaseModel):
    """Single entry in a trace timeline."""
    timestamp: float = Field(..., description="Unix timestamp")
    type: str = Field(..., description="Type: retrieval, tool_call, llm_call, decision")
    details: Dict[str, Any] = Field(..., description="Type-specific details")


class Trace(BaseModel):
    """Complete trace for a request."""
    request_id: str
    question: str
    customer_id: str
    timeline: List[TraceEntry] = Field(..., description="Chronological list of events")
    total_llm_calls: int
    total_tool_calls: int
    total_retries: int

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req_123",
                "question": "What's my refund policy?",
                "customer_id": "cust_001",
                "timeline": [
                    {
                        "timestamp": 1696012800.0,
                        "type": "retrieval",
                        "details": {
                            "query": "refund policy",
                            "chunks": [
                                {
                                    "source": "refund_basic.md",
                                    "content": "Basic tier customers can request a full refund within 7 days...",
                                    "score": 0.89
                                }
                            ]
                        }
                    },
                    {
                        "timestamp": 1696012801.5,
                        "type": "tool_call",
                        "details": {
                            "tool": "get_account_status",
                            "params": {"customer_id": "cust_001"},
                            "result": {"status": "active", "tier": "basic"},
                            "retry_count": 0
                        }
                    },
                    {
                        "timestamp": 1696012802.0,
                        "type": "llm_call",
                        "details": {
                            "model": "openai/gpt-oss-20b",
                            "tokens": 512,
                            "purpose": "synthesize_answer"
                        }
                    }
                ],
                "total_llm_calls": 2,
                "total_tool_calls": 1,
                "total_retries": 0
            }
        }
