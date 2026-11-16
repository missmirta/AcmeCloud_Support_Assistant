"""
Backend for AcmeCloud services.
Provides account, billing, and ticketing APIs.

DO NOT MODIFY THIS FILE - it represents upstream systems you must work with.
"""

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime, timedelta
import random

from chaos import ChaosEngine
from audit import AuditLog
from data import get_customer_data, get_billing_data, create_ticket, get_payment_method

app = FastAPI(title="AcmeCloud Backend")

# Initialize chaos engine
# Simulates real-world API unreliability
chaos = ChaosEngine(chaos_level=0.5, seed=42)

# Initialize audit log
audit = AuditLog()


class TicketRequest(BaseModel):
    customer_id: str
    issue: str
    priority: str = "P3"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/account/{customer_id}")
def get_account(customer_id: str):
    """Get customer account status."""
    audit.log("GET", f"/account/{customer_id}", {})

    # Check for chaos
    failure = chaos.should_fail()
    if failure:
        audit.log_failure("GET", f"/account/{customer_id}", failure)
        if failure["type"] == "timeout":
            import time
            time.sleep(failure["delay"])
            raise HTTPException(status_code=504, detail="Gateway Timeout")
        elif failure["type"] == "rate_limit":
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded, try again later",
                headers={"Retry-After": "5"}
            )
        elif failure["type"] == "service_error":
            raise HTTPException(status_code=503, detail="Upstream service temporarily unavailable")
        elif failure["type"] == "stale_data":
            # Return stale account status
            data = get_customer_data(customer_id)
            if data["status"] == "suspended":
                # Return "active" as stale data
                data = data.copy()
                data["status"] = "active"
                stale_time = datetime.now() - timedelta(hours=random.randint(24, 72))
                data["as_of"] = stale_time.isoformat()
                audit.log_response("GET", f"/account/{customer_id}", data, stale=True)
                return data

    # Normal response
    data = get_customer_data(customer_id)
    data["as_of"] = datetime.now().isoformat()
    audit.log_response("GET", f"/account/{customer_id}", data)
    return data


@app.get("/billing/{customer_id}")
def get_billing(customer_id: str):
    """Get customer billing history."""
    audit.log("GET", f"/billing/{customer_id}", {})

    # Check for chaos
    failure = chaos.should_fail()
    if failure:
        audit.log_failure("GET", f"/billing/{customer_id}", failure)
        if failure["type"] == "timeout":
            import time
            time.sleep(failure["delay"])
            raise HTTPException(status_code=504, detail="Gateway Timeout")
        elif failure["type"] == "rate_limit":
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded, try again later",
                headers={"Retry-After": "5"}
            )
        elif failure["type"] == "service_error":
            raise HTTPException(status_code=503, detail="Upstream service temporarily unavailable")
        elif failure["type"] == "stale_data":
            # Return billing data with old as_of timestamp
            data = get_billing_data(customer_id)
            stale_time = datetime.now() - timedelta(hours=random.randint(25, 72))
            data["as_of"] = stale_time.isoformat()
            audit.log_response("GET", f"/billing/{customer_id}", data, stale=True)
            return data

    # Normal response
    data = get_billing_data(customer_id)
    data["as_of"] = datetime.now().isoformat()
    audit.log_response("GET", f"/billing/{customer_id}", data)
    return data


@app.post("/tickets")
def create_support_ticket(
    request: TicketRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Create a support ticket. Supports idempotency."""
    audit.log("POST", "/tickets", {"body": request.dict(), "idempotency_key": idempotency_key})

    # Check for chaos
    failure = chaos.should_fail()
    if failure:
        audit.log_failure("POST", "/tickets", failure)
        if failure["type"] == "timeout":
            import time
            time.sleep(failure["delay"])
            raise HTTPException(status_code=504, detail="Gateway Timeout")
        elif failure["type"] == "rate_limit":
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded, try again later",
                headers={"Retry-After": "5"}
            )
        elif failure["type"] == "service_error":
            raise HTTPException(status_code=503, detail="Upstream service temporarily unavailable")

    # Create ticket
    ticket_id = create_ticket(
        customer_id=request.customer_id,
        issue=request.issue,
        priority=request.priority,
        idempotency_key=idempotency_key
    )

    response = {
        "ticket_id": ticket_id,
        "status": "created",
        "customer_id": request.customer_id,
        "priority": request.priority
    }

    audit.log_response("POST", "/tickets", response)
    return response


@app.get("/payment-method/{payment_method_id}")
def get_payment_method_info(payment_method_id: str):
    """Get payment method details."""
    audit.log("GET", f"/payment-method/{payment_method_id}", {})

    # Check for chaos
    failure = chaos.should_fail()
    if failure:
        audit.log_failure("GET", f"/payment-method/{payment_method_id}", failure)
        if failure["type"] == "timeout":
            import time
            time.sleep(failure["delay"])
            raise HTTPException(status_code=504, detail="Gateway Timeout")
        elif failure["type"] == "rate_limit":
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded, try again later",
                headers={"Retry-After": "5"}
            )
        elif failure["type"] == "service_error":
            raise HTTPException(status_code=503, detail="Upstream service temporarily unavailable")
        elif failure["type"] == "stale_data":
            # Return payment method data with old expiry (appears valid but actually expired)
            data = get_payment_method(payment_method_id)
            if data.get("exp_year") == 2024 and data.get("exp_month", 0) < 12:
                # Make expired card appear valid
                data = data.copy()
                data["exp_year"] = 2026
                stale_time = datetime.now() - timedelta(hours=random.randint(30, 72))
                data["as_of"] = stale_time.isoformat()
                audit.log_response("GET", f"/payment-method/{payment_method_id}", data, stale=True)
                return data

    # Normal response
    data = get_payment_method(payment_method_id)
    data["as_of"] = datetime.now().isoformat()
    audit.log_response("GET", f"/payment-method/{payment_method_id}", data)
    return data


@app.get("/usage/{customer_id}")
def get_usage_stats(customer_id: str, month: Optional[str] = None):
    """Get API usage statistics for customer."""
    audit.log("GET", f"/usage/{customer_id}", {"month": month})

    # Check for chaos
    failure = chaos.should_fail()
    if failure:
        audit.log_failure("GET", f"/usage/{customer_id}", failure)
        if failure["type"] == "timeout":
            import time
            time.sleep(failure["delay"])
            raise HTTPException(status_code=504, detail="Gateway Timeout")
        elif failure["type"] == "rate_limit":
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded, try again later",
                headers={"Retry-After": "5"}
            )
        elif failure["type"] == "service_error":
            raise HTTPException(status_code=503, detail="Upstream service temporarily unavailable")

    # Get customer data to determine tier
    customer = get_customer_data(customer_id)
    tier = customer["tier"]

    # Generate realistic usage data based on tier
    if tier == "basic":
        hourly_requests = random.randint(200, 900)  # Under 1000/hour limit
        monthly_requests = random.randint(100000, 600000)
    else:  # enterprise
        hourly_requests = random.randint(2000, 8000)  # Under 10000/hour limit
        monthly_requests = random.randint(1000000, 5000000)

    data = {
        "customer_id": customer_id,
        "tier": tier,
        "current_hour_requests": hourly_requests,
        "monthly_requests": monthly_requests,
        "as_of": datetime.now().isoformat()
    }

    audit.log_response("GET", f"/usage/{customer_id}", data)
    return data


@app.get("/audit/log")
def get_audit_log():
    """Get audit log (for testing/review)."""
    return audit.get_log()


@app.post("/audit/clear")
def clear_audit_log():
    """Clear audit log (for testing)."""
    audit.clear()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
