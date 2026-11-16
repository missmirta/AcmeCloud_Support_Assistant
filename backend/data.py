"""
Mock customer data for the backend.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid

# Mock customer database
CUSTOMERS = {
    "cust_001": {
        "customer_id": "cust_001",
        "email": "user1@example.com",
        "tier": "basic",
        "status": "active",
        "created_at": "2024-01-15T00:00:00Z",
        "payment_method_id": "pm_001"
    },
    "cust_002": {
        "customer_id": "cust_002",
        "email": "user2@example.com",
        "tier": "basic",
        "status": "active",
        "created_at": "2024-03-20T00:00:00Z",
        "payment_method_id": "pm_002"
    },
    "cust_003": {
        "customer_id": "cust_003",
        "email": "user3@example.com",
        "tier": "enterprise",
        "status": "active",
        "created_at": "2024-02-10T00:00:00Z",
        "payment_method_id": "pm_003"
    },
    "cust_004": {
        "customer_id": "cust_004",
        "email": "user4@example.com",
        "tier": "enterprise",
        "status": "active",
        "created_at": "2023-12-01T00:00:00Z",
        "payment_method_id": "pm_004"
    },
    "cust_005": {
        "customer_id": "cust_005",
        "email": "user5@example.com",
        "tier": "basic",
        "status": "active",
        "created_at": "2024-06-15T00:00:00Z",
        "payment_method_id": "pm_005"
    },
    "cust_006": {
        "customer_id": "cust_006",
        "email": "user6@example.com",
        "tier": "basic",
        "status": "canceled",
        "created_at": "2024-01-05T00:00:00Z",
        "canceled_at": "2024-09-29T00:00:00Z",
        "payment_method_id": None
    },
    "cust_007": {
        "customer_id": "cust_007",
        "email": "user7@example.com",
        "tier": "enterprise",
        "status": "suspended",
        "created_at": "2024-05-01T00:00:00Z",
        "suspended_at": "2024-09-28T00:00:00Z",
        "payment_method_id": "pm_007"
    }
}

# Mock billing data
BILLING = {
    "cust_001": {
        "balance": 0.0,
        "last_charge": {"amount": 15.0, "date": "2024-09-01T00:00:00Z", "description": "Monthly subscription - Basic"},
        "next_charge": "2024-10-01T00:00:00Z"
    },
    "cust_002": {
        "balance": 0.0,
        "last_charge": {"amount": 15.0, "date": "2024-09-20T00:00:00Z", "description": "Monthly subscription - Basic"},
        "next_charge": "2024-10-20T00:00:00Z"
    },
    "cust_003": {
        "balance": 45.0,
        "last_charge": {"amount": 75.0, "date": "2024-09-10T00:00:00Z", "description": "Monthly subscription - Enterprise"},
        "next_charge": "2024-10-10T00:00:00Z"
    },
    "cust_004": {
        "balance": 0.0,
        "last_charge": {"amount": 50.0, "date": "2024-08-15T00:00:00Z", "description": "Monthly subscription - Enterprise (legacy pricing)"},
        "next_charge": "2024-10-01T00:00:00Z"
    },
    "cust_005": {
        "balance": 0.0,
        "last_charge": {"amount": 15.0, "date": "2024-09-25T00:00:00Z", "description": "Monthly subscription - Basic"},
        "next_charge": "2024-10-25T00:00:00Z"
    },
    "cust_006": {
        "balance": 0.0,
        "last_charge": {"amount": 15.0, "date": "2024-09-05T00:00:00Z", "description": "Monthly subscription - Basic"},
        "next_charge": None
    },
    "cust_007": {
        "balance": 75.0,
        "last_charge": {"amount": 75.0, "date": "2024-09-01T00:00:00Z", "description": "Monthly subscription - Enterprise"},
        "next_charge": "2024-10-01T00:00:00Z"
    }
}

# Payment methods
PAYMENT_METHODS = {
    "pm_001": {"type": "card", "last4": "4242", "exp_month": 12, "exp_year": 2025},
    "pm_002": {"type": "card", "last4": "5555", "exp_month": 6, "exp_year": 2026},
    "pm_003": {"type": "card", "last4": "9999", "exp_month": 3, "exp_year": 2027},
    "pm_004": {"type": "bank", "account_last4": "6789"},
    "pm_005": {"type": "card", "last4": "1111", "exp_month": 1, "exp_year": 2025},  # Expires soon!
    "pm_007": {"type": "card", "last4": "8888", "exp_month": 11, "exp_year": 2024},  # EXPIRED!
}

# Ticket tracking (for idempotency)
TICKETS = {}
TICKET_BY_IDEMPOTENCY = {}


def get_customer_data(customer_id: str) -> Dict[str, Any]:
    """Get customer account data."""
    if customer_id not in CUSTOMERS:
        raise ValueError(f"Customer {customer_id} not found")
    return CUSTOMERS[customer_id].copy()


def get_billing_data(customer_id: str) -> Dict[str, Any]:
    """Get billing data."""
    if customer_id not in BILLING:
        raise ValueError(f"Billing data for {customer_id} not found")
    return BILLING[customer_id].copy()


def get_payment_method(payment_method_id: str) -> Dict[str, Any]:
    """Get payment method details."""
    if not payment_method_id or payment_method_id not in PAYMENT_METHODS:
        raise ValueError(f"Payment method {payment_method_id} not found")
    return PAYMENT_METHODS[payment_method_id].copy()


def create_ticket(
    customer_id: str,
    issue: str,
    priority: str,
    idempotency_key: Optional[str] = None
) -> str:
    """
    Create a support ticket.

    If idempotency_key is provided and matches an existing ticket,
    returns the existing ticket ID instead of creating a duplicate.
    """
    # Check idempotency
    if idempotency_key and idempotency_key in TICKET_BY_IDEMPOTENCY:
        return TICKET_BY_IDEMPOTENCY[idempotency_key]

    # Create new ticket
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"

    TICKETS[ticket_id] = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "issue": issue,
        "priority": priority,
        "created_at": datetime.now().isoformat(),
        "status": "open"
    }

    # Store idempotency mapping
    if idempotency_key:
        TICKET_BY_IDEMPOTENCY[idempotency_key] = ticket_id

    return ticket_id
