"""The refund form: only typed values get through, and the text is written by code."""

from datetime import date

from mcp_client import ToolOutcome
from refund import Excerpt, RefundForm, days_since_last_charge, form_schema, parse_form, render_answer

EXCERPTS = {
    "refund_basic.md": Excerpt("Basic tier customers can request a full refund within 7 days of payment.", "basic"),
    "refund_enterprise.md": Excerpt("Enterprise refunds are available within 30 days of payment.", "enterprise"),
    "pricing_2024_q3.md": Excerpt("The enterprise list price is $75 per user per month.", None),
}
ACCOUNT_TIER = "enterprise"
ACCOUNT = ToolOutcome(result={"tier": "enterprise", "status": "active", "as_of": "2026-11-15T10:00:00"})
BILLING = ToolOutcome(result={"last_charge": {
    "amount": 50.0, "date": "2024-08-15T00:00:00Z", "description": "Enterprise (legacy pricing)",
}})


def test_window_must_appear_in_the_document_it_cites():
    # The model's number is checked against the cited text: 7 is not stated there, so it is dropped
    # together with the verdict that depends on it; the window is read from the tier's own policy.
    form = parse_form({"window_days": 7, "source": "refund_enterprise.md", "needs_human": False}, EXCERPTS, ACCOUNT_TIER)
    assert form == RefundForm(window_days=30, source="refund_enterprise.md", needs_human=True)
    assert "7 days" not in render_answer(form, ACCOUNT, BILLING, None)


def test_the_charge_record_decides_the_verdict_and_customer_days_only_fill_a_gap():
    # Regression: "last month" was turned into 30 days and a 2024 charge was called "inside" a 30-day window.
    charged = ToolOutcome(result={"last_charge": {"amount": 50.0, "date": "2024-08-15T00:00:00Z"}})
    assert days_since_last_charge(charged, date(2026, 11, 16)) == 823
    assert days_since_last_charge(ToolOutcome(result={}), date(2026, 11, 16)) is None
    args = {"window_days": 30, "source": "refund_enterprise.md", "days_since_payment": 30, "needs_human": False}
    assert parse_form(args, EXCERPTS, ACCOUNT_TIER, days_since_charge=823).within_window == "no"
    assert parse_form(args, EXCERPTS, ACCOUNT_TIER, days_since_charge=10).within_window == "yes"
    assert parse_form(args, EXCERPTS, ACCOUNT_TIER).within_window == "yes"
    assert parse_form({**args, "days_since_payment": 45}, EXCERPTS, ACCOUNT_TIER).within_window == "no"


def test_without_a_form_the_window_comes_from_the_tier_policy():
    form = parse_form({}, EXCERPTS, "basic")
    assert (form.window_days, form.source, form.within_window) == (7, "refund_basic.md", "unknown")
    assert "7 days [refund_basic.md]" in render_answer(form, ACCOUNT, BILLING, None)
    # No policy text for the tier, or no tier: the window stays undetermined.
    assert parse_form({}, {"x.md": EXCERPTS["pricing_2024_q3.md"]}, "basic").window_days is None
    assert parse_form({}, EXCERPTS, None).window_days is None


def test_unknown_verdict_goes_to_a_human():
    args = {"window_days": 7, "source": "refund_basic.md", "days_since_payment": -1, "needs_human": False}
    form = parse_form(args, EXCERPTS, "basic")
    assert form.within_window == "unknown"
    assert form.needs_human is True


