# Webhook Integration Guide

*Updated: June 2024*

## Overview

Webhooks allow AcmeCloud to send real-time notifications to your application when events occur.

## Webhook Limits

- **Basic tier**: 2 webhook endpoints
- **Enterprise tier**: 50 webhook endpoints

## Supported Events

### Account Events
- `account.created` - New account created
- `account.updated` - Account details changed
- `account.suspended` - Account suspended
- `account.canceled` - Account canceled

### Billing Events
- `invoice.created` - New invoice generated
- `invoice.paid` - Invoice payment succeeded
- `invoice.payment_failed` - Invoice payment failed
- `payment_method.expiring` - Payment method expiring in 30 days
- `payment_method.expired` - Payment method expired

### Storage Events
- `storage.limit_approaching` - Storage at 80% of limit
- `storage.limit_exceeded` - Storage exceeded tier limit

### Support Events
- `ticket.created` - New support ticket created
- `ticket.updated` - Ticket status changed
- `ticket.resolved` - Ticket marked resolved

## Setting Up Webhooks

### 1. Create Endpoint

Configure your server to receive POST requests:

```python
@app.post("/webhooks/acmecloud")
async def handle_webhook(request):
    payload = await request.json()
    signature = request.headers.get("X-AcmeCloud-Signature")
    
    # Verify signature
    if not verify_signature(payload, signature):
        return {"error": "Invalid signature"}, 401
    
    # Process event
    event_type = payload["type"]
    if event_type == "invoice.payment_failed":
        handle_payment_failure(payload["data"])
    
    return {"received": True}
```

### 2. Register Webhook

In dashboard:
1. Go to Settings > Webhooks
2. Click "Add Webhook"
3. Enter endpoint URL (must be HTTPS)
4. Select events to subscribe to
5. Note your webhook secret

### 3. Verify Signatures

All webhook requests include `X-AcmeCloud-Signature` header for authentication:

```python
import hmac
import hashlib

def verify_signature(payload, signature):
    secret = os.getenv("WEBHOOK_SECRET")
    computed = hmac.new(
        secret.encode(),
        json.dumps(payload).encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)
```

**Always verify signatures** to prevent unauthorized webhook calls.

## Webhook Payload Format

```json
{
  "id": "evt_1a2b3c4d",
  "type": "invoice.payment_failed",
  "created_at": "2024-09-30T12:34:56Z",
  "data": {
    "customer_id": "cust_007",
    "invoice_id": "inv_abc123",
    "amount": 75.00,
    "reason": "card_declined"
  }
}
```

## Delivery & Retries

### Delivery Expectations

- Webhooks sent within 5 seconds of event
- Expect 200-299 status code within 10 seconds
- Timeout after 10 seconds
- Any other status code considered failure

### Retry Logic

On failure, webhooks are retried:
1. After 1 minute
2. After 10 minutes
3. After 1 hour
4. After 6 hours
5. After 24 hours

After 5 failed attempts, webhook endpoint is disabled. Check Settings > Webhooks > Delivery History for failures.

## Best Practices

### Idempotency

Webhooks may be delivered multiple times. Design handlers to be idempotent:

```python
processed_events = set()

def handle_webhook(payload):
    event_id = payload["id"]
    
    # Check if already processed
    if event_id in processed_events:
        return {"received": True}
    
    # Process event
    process_event(payload)
    
    # Mark as processed
    processed_events.add(event_id)
    return {"received": True}
```

### Async Processing

Respond quickly (< 1 second) to avoid timeouts:

```python
@app.post("/webhooks/acmecloud")
async def handle_webhook(request):
    payload = await request.json()
    
    # Verify signature
    verify_signature(payload)
    
    # Queue for async processing
    await event_queue.put(payload)
    
    # Respond immediately
    return {"received": True}
```

### Error Handling

```python
@app.post("/webhooks/acmecloud")
async def handle_webhook(request):
    try:
        payload = await request.json()
        verify_signature(payload)
        await process_event(payload)
        return {"received": True}
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        # Return 200 to prevent retries for known bad data
        if isinstance(e, ValidationError):
            return {"received": False, "error": str(e)}
        # Return 500 for transient errors to trigger retry
        raise
```

### Security

1. **Always use HTTPS** for webhook endpoints
2. **Verify signatures** on every request
3. **Validate payload structure** before processing
4. **Store webhook secret securely** (environment variable, not code)
5. **Log webhook deliveries** for debugging
6. **Rate limit** webhook endpoint to prevent abuse

## Testing Webhooks

### Test Mode

Send test webhooks from dashboard:
1. Settings > Webhooks
2. Select webhook endpoint
3. Click "Send Test Event"
4. Choose event type
5. View delivery status

### Local Development

Use tools like ngrok to expose local server:

```bash
ngrok http 8000
```

Use ngrok URL as webhook endpoint during development.

## Monitoring

### Delivery History

View webhook delivery history:
- Settings > Webhooks > Delivery History
- Shows last 100 deliveries per endpoint
- Includes status code, response time, retry count

### Alerts

Configure alerts for webhook failures:
- 5 consecutive failures
- Endpoint disabled
- High failure rate (>10% over 1 hour)

## Troubleshooting

### Webhooks Not Received

1. Check endpoint is HTTPS
2. Verify endpoint returns 200-299 status
3. Check firewall allows AcmeCloud IPs
4. Review delivery history for error messages
5. Ensure endpoint responds within 10 seconds

### Signature Verification Fails

1. Verify you're using correct webhook secret
2. Ensure payload is not modified before verification
3. Check payload is serialized consistently
4. Confirm you're using SHA-256 HMAC

### High Retry Rate

1. Ensure endpoint returns 2xx status quickly
2. Implement async processing
3. Add timeout handling
4. Check for memory leaks or resource exhaustion

For webhook support, contact support@acmecloud.com with:
- Webhook endpoint ID
- Recent delivery timestamps
- Error messages from delivery history
