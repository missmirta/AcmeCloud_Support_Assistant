"""The refund form: only typed values get through, and the text is written by code."""

from mcp_client import ToolOutcome
from refund import Excerpt, RefundForm, form_schema, parse_form, render_answer

EXCERPTS = {
    "refund_basic.md": Excerpt("Basic tier customers can request a full refund within 7 days of payment.", "basic"),
    "refund_enterprise.md": Excerpt("Enterprise refunds are available within 30 days of payment.", "enterprise"),
    "pricing_2024_q3.md": Excerpt("The enterprise list price is $75 per user per month.", None),
}
SOURCES = list(EXCERPTS)
ACCOUNT_TIER = "enterprise"
ACCOUNT = ToolOutcome(result={"tier": "enterprise", "status": "active", "as_of": "2026-11-15T10:00:00"})
BILLING = ToolOutcome(result={"last_charge": {
    "amount": 50.0, "date": "2024-08-15T00:00:00Z", "description": "Enterprise (legacy pricing)",
}})
PROMISE = "Your refund has been approved"










def test_window_must_appear_in_the_document_it_cites():
    # The model's number is checked against the cited text: 7 is not stated there, so it is dropped
    # together with the verdict that depends on it.
    form = parse_form({"window_days": 7, "source": "refund_enterprise.md", "within_window": "no",
                       "needs_human": False}, EXCERPTS, ACCOUNT_TIER)
    assert form == RefundForm(needs_human=False)
    assert "7 days" not in render_answer(form, ACCOUNT, BILLING, None)










