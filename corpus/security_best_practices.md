# Security Best Practices

*Last reviewed: April 2024*

## Account Security

### Password Requirements

- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, and symbols
- No common dictionary words
- Changed every 90 days (recommended)
- No password reuse

### Two-Factor Authentication

**Strongly recommended for all accounts. Required for:**
- Admin users
- Users with billing access
- Enterprise tier accounts (can be enforced org-wide)

**Supported methods:**
- Authenticator app (recommended)
- SMS verification
- Hardware security keys (FIDO2/WebAuthn)

### Session Management

- Sessions expire after 12 hours of inactivity
- Active sessions visible in Settings > Security
- Can revoke individual sessions
- IP address logged for each session

## API Security

### API Key Management

**Best practices:**
1. **Rotate regularly** - Every 90 days minimum
2. **Use separate keys** for different environments (dev, staging, prod)
3. **Never commit keys** to version control
4. **Store securely** - Use environment variables or secret managers
5. **Revoke unused keys** immediately

### API Key Permissions

Limit API key permissions to minimum required:
- Read-only for reporting/analytics
- Write permissions only when necessary
- Never share API keys between applications

### Request Authentication

All API requests must include:
```
Authorization: Bearer YOUR_API_KEY
```

Requests without valid authentication return `401 Unauthorized`.

## Data Protection

### Encryption

- **In transit**: TLS 1.3 for all connections
- **At rest**: AES-256 encryption for all stored data
- **Backups**: Encrypted with separate keys

### Data Access

- Follow principle of least privilege
- Review team permissions quarterly
- Remove access immediately when team members leave
- Use role-based access control (Enterprise)

### Data Retention

- Basic tier: 30-day backup retention
- Enterprise tier: 90-day backup retention
- Deleted data purged after retention period
- See data retention policy for details

## Network Security

### IP Allowlisting (Enterprise Only)

Restrict API access to specific IP ranges:
1. Go to Settings > Security > IP Allowlist
2. Add IP addresses or CIDR ranges
3. Enable enforcement
4. Test thoroughly before full rollout

**Warning**: Incorrect configuration can lock you out.

### Webhook Security

Verify webhook authenticity:
- Check `X-AcmeCloud-Signature` header
- Use webhook secret for HMAC validation
- Validate timestamp to prevent replay attacks
- Use HTTPS endpoints only

## Compliance

### SOC 2 Type II

Enterprise tier includes SOC 2 Type II compliance. Report available upon request.

### GDPR

AcmeCloud is GDPR compliant:
- Right to access data
- Right to deletion
- Data portability
- EU data residency available (Enterprise)

### HIPAA (Enterprise Add-On)

HIPAA compliance available for Enterprise customers:
- Business Associate Agreement (BAA) required
- Additional $1,000/month
- Dedicated HIPAA-compliant infrastructure
- Additional audit logging
- Contact sales@acmecloud.com

## Incident Response

### Reporting Security Issues

**Found a security vulnerability?**
- Email: security@acmecloud.com
- Do not disclose publicly
- Include steps to reproduce
- We respond within 48 hours
- Responsible disclosure appreciated

### Breach Notification

In case of data breach:
- Affected customers notified within 72 hours
- Details provided via email and dashboard notification
- Incident report available upon request

## Security Monitoring

### Audit Logs

Available in Settings > Security > Audit Logs:
- All API requests
- Login attempts (successful and failed)
- Permission changes
- Data access events
- Configuration changes

**Retention:**
- Basic: 30 days
- Enterprise: 1 year
- Export available in CSV/JSON format

### Alerts

Configure security alerts for:
- Failed login attempts (5+ in 10 minutes)
- API key usage from new IP addresses
- Permission changes
- High-volume API usage
- Data export operations

## Regular Security Review

Recommended quarterly:
- Review active team members
- Audit API keys and permissions
- Check for unused integrations
- Review audit logs for anomalies
- Update passwords and rotate keys
- Verify backup integrity

For security questions, contact security@acmecloud.com.
