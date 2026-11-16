"""
Refund questions: the model fills in a typed form, the code writes the answer.

The assistant must never tell a customer that a refund has been, or will be,
given. Free text cannot be checked for that with certainty, so on this path the
model writes no text at all. It returns numbers, flags and file names chosen
from a fixed list; every sentence the customer reads is assembled here from
those fields and from tool results. None of the field types can carry a promise.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mcp_client import ToolOutcome

FORM_NAME = "refund_form"
_VERDICTS = {"yes", "no", "unknown"}

FORM_INSTRUCTION = (
    "This is a refund question. The account and billing data above were looked up for you. "
    f"Do not write an answer. Call {FORM_NAME} and fill it in from the knowledge-base excerpts "
    "and the tool results. Use the policy for the tier reported by get_account_status and, "
    "where excerpts conflict, the most recently dated one."
)


@dataclass(frozen=True)
class Excerpt:
    """Retrieved text of one knowledge-base file, with the tier its header names (if any)."""
    text: str
    tier: Optional[str] = None


def form_schema(sources: List[str]) -> Dict[str, Any]:
    """The form as a tool schema. File names are limited to the retrieved documents."""
    return {
        "type": "function",
        "function": {
            "name": FORM_NAME,
            "description": "Report the facts needed to answer the customer's refund question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": {
                        "type": "integer",
                        "description": "Length in days of the refund window that applies to this customer's tier",
                    },
                    "source": {
                        "type": "string",
                        "enum": sources,
                        "description": "Knowledge-base file that states this refund window",
                    },
                    "within_window": {
                        "type": "string",
                        "enum": sorted(_VERDICTS),
                        "description": "Whether the payment in question falls inside the window, judged from "
                        "the dates the customer gave and the billing data; 'unknown' if it cannot be told",
                    },
                    "needs_human": {
                        "type": "boolean",
                        "description": "true if the customer wants a refund given, approved or reviewed, or "
                        "disputes a charge; false if they only ask what the policy is or whether they qualify",
                    },
                    "current_price": {
                        "type": "number",
                        "description": "Only if the customer asks about a price: the current list price in "
                        "USD per user per month for their tier",
                    },
                    "price_source": {
                        "type": "string",
                        "enum": sources,
                        "description": "Knowledge-base file that states current_price",
                    },
                },
                "required": ["window_days", "source", "within_window", "needs_human"],
            },
        },
    }


@dataclass
class RefundForm:
    window_days: Optional[int] = None
    source: Optional[str] = None
    within_window: str = "unknown"
    # Fail safe: if the model did not return a usable form, a human gets the case.
    needs_human: bool = True
    current_price: Optional[float] = None
    price_source: Optional[str] = None

    @property
    def sources(self) -> List[str]:
        return list(dict.fromkeys(s for s in (self.source, self.price_source) if s))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _window_stated(days: int, text: str) -> bool:
    """The number must appear as a window ("30 days", "30-day") in the document that cites it."""
    return re.search(rf"\b{days}[- ]days?\b", text, re.IGNORECASE) is not None


def _applies_to_tier(excerpt: "Excerpt", account_tier: Any) -> bool:
    """The cited document must be the policy for this customer's tier, not another tier's."""
    return isinstance(account_tier, str) and excerpt.tier is not None and excerpt.tier == account_tier.strip().lower()


def parse_form(args: Dict[str, Any], excerpts: Dict[str, "Excerpt"], account_tier: Any) -> RefundForm:
    """Keep only values of the expected type; anything else is dropped, never shown.

    `excerpts` maps each retrieved file name to its text and tier. A window is kept
    only when the file the model cites is the policy for `account_tier` and states
    that number of days; otherwise the answer says the window could not be determined.
    """
    form = RefundForm()
    window, source = args.get("window_days"), args.get("source")
    if (_is_number(window) and float(window).is_integer() and 0 < window <= 3650
            and isinstance(source, str) and source in excerpts
            and _applies_to_tier(excerpts[source], account_tier)
            and _window_stated(int(window), excerpts[source].text)):
        form.window_days, form.source = int(window), source
        if args.get("within_window") in _VERDICTS:
            form.within_window = args["within_window"]
    if isinstance(args.get("needs_human"), bool):
        form.needs_human = args["needs_human"]
    price, price_source = args.get("current_price"), args.get("price_source")
    if _is_number(price) and 0 < price < 1_000_000 and isinstance(price_source, str) and price_source in excerpts:
        form.current_price, form.price_source = float(price), price_source
    return form


def _money(amount: Any) -> str:
    return f"${amount:,.2f}" if _is_number(amount) else "an unknown amount"


def _freshness(outcome: ToolOutcome) -> str:
    as_of = (outcome.result or {}).get("as_of")
    if outcome.stale:
        return f" This data may be out of date (as of {as_of})."
    return ""


def _account_line(account: ToolOutcome) -> str:
    if not account.result:
        return "Your account details could not be retrieved right now."
    return (
        f"Your account, as verified: {account.result.get('tier', 'unknown')} tier, "
        f"status {account.result.get('status', 'unknown')}.{_freshness(account)}"
    )


def _billing_line(billing: ToolOutcome) -> Optional[str]:
    charge = (billing.result or {}).get("last_charge")
    if isinstance(charge, dict):
        description = f" ({charge['description']})" if charge.get("description") else ""
        return (
            f"Last charge on record: {_money(charge.get('amount'))} on "
            f"{str(charge.get('date', 'an unknown date'))[:10]}{description}.{_freshness(billing)}"
        )
    if billing.result is None:
        return "Your billing history could not be retrieved right now."
    return None


def _ticket_line(ticket: Optional[ToolOutcome]) -> Optional[str]:
    if ticket is None:
        return None
    if ticket.result and ticket.result.get("ticket_id"):
        return f"Ticket {ticket.result['ticket_id']} has been opened and a human agent will review your request."
    return "A ticket could not be opened right now; please contact support so a human agent can review your request."


def render_lookup_answer(outcomes: Dict[str, ToolOutcome]) -> str:
    """
    Answer from tool data alone, for when no LLM call is left to write one.
    Only the tools that actually ran are reported.
    """
    lines = []
    if "get_account_status" in outcomes:
        lines.append(_account_line(outcomes["get_account_status"]))
    if "get_billing_history" in outcomes:
        lines.append(_billing_line(outcomes["get_billing_history"]))
    lines.append(_ticket_line(outcomes.get("escalate_to_human")))
    return "\n".join(line for line in lines if line)


def render_answer(
    form: RefundForm,
    account: ToolOutcome,
    billing: ToolOutcome,
    ticket: Optional[ToolOutcome],
) -> str:
    """The customer-facing answer. Every sentence is written here."""
    lines = ["I can't approve or promise a refund; that decision is made by a human agent."]

    lines.append(_account_line(account))
    billing_line = _billing_line(billing)
    if billing_line:
        lines.append(billing_line)

    if form.current_price is not None:
        lines.append(
            f"The current list price for your tier is {_money(form.current_price)} "
            f"per user per month [{form.price_source}]."
        )

    if form.window_days is not None:
        lines.append(
            f"Under the refund policy for your tier, the refund window is {form.window_days} days [{form.source}]."
        )
        if form.within_window == "no":
            lines.append("From the dates available, the payment appears to be outside that window.")
        elif form.within_window == "yes":
            lines.append(
                "From the dates available, the payment appears to be inside that window; "
                "a human agent still has to confirm this and make the decision."
            )
    else:
        lines.append("I could not determine the refund window that applies to you from the knowledge base.")

    lines.append(_ticket_line(ticket) or "If you would like a refund request reviewed, say so and it will be passed to a human agent.")

    return "\n".join(lines)
