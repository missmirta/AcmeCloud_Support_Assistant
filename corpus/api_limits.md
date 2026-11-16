# API Rate Limits

*Last updated: March 2024*

## Standard Rate Limits

All API requests are subject to rate limiting to ensure fair usage and system stability.

### Basic Tier
- **1,000 requests per hour** per account
- **50 requests per minute** per API key
- Burst allowance: up to 100 requests in 10 seconds

### Enterprise Tier
- **10,000 requests per hour** per account
- **500 requests per minute** per API key
- Burst allowance: up to 1,000 requests in 10 seconds

## Rate Limit Headers

All API responses include rate limit information:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1630454400
```

## Exceeding Rate Limits

When you exceed your rate limit:
- HTTP status code: **429 Too Many Requests**
- Response includes `Retry-After` header (in seconds)
- Recommended: implement exponential backoff
- Minimum retry delay: 1 second

## Best Practices

1. Cache responses when possible
2. Implement retry logic with exponential backoff
3. Monitor your rate limit headers
4. Consider upgrading to Enterprise for higher limits
5. Use batch endpoints where available

## Temporary Rate Limit Increases

Enterprise customers can request temporary rate limit increases for special events. Contact support at least 48 hours in advance.
