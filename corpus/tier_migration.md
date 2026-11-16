# Tier Migration Guide

*Published: May 2024*

## Upgrading to Enterprise

### Process

1. **Navigate to Billing Settings**
   - Go to Settings > Billing > Change Plan
   - Select Enterprise tier
   - Review pricing and features

2. **Complete Upgrade**
   - Confirm upgrade
   - Charges are pro-rated for the current billing period
   - New features activate immediately

3. **Post-Upgrade Setup**
   - Configure SSO (if needed)
   - Set up additional team members
   - Configure advanced security settings
   - Schedule onboarding call with account manager

### Billing

- Pro-rated charges for remainder of current billing period
- Example: Upgrading mid-month from Basic ($15) to Enterprise ($75)
  - Receive credit for unused Basic time
  - Charged pro-rated Enterprise amount
- Next full billing cycle: full Enterprise price

### No Downtime

Upgrades are instant with zero downtime. All existing data, API keys, and configurations remain intact.

## Downgrading to Basic

### Important Considerations

⚠️ **Data Loss Warning**: Downgrading may result in data loss if you exceed Basic tier limits.

### Pre-Downgrade Checklist

Before downgrading, ensure:

1. **Storage**: Each user has ≤ 100 GB data
   - Archive or delete excess data
   - Download important files locally
   - Allow 24 hours for storage recalculation

2. **API Usage**: Current usage fits Basic limits
   - Review API call patterns
   - Reduce webhook endpoints to 2 or fewer
   - Delete extra API keys (keep max 2)

3. **Team Size**: Reduce to 5 team members or fewer
   - Remove inactive users
   - Reassign ownership of critical resources

4. **Features**: Disable Enterprise-only features
   - Disable SSO (users will need passwords)
   - Export audit logs if needed
   - Remove IP allowlist rules

### Features You'll Lose

- SSO/SAML authentication
- Priority 24/7 support
- Dedicated account manager
- Advanced analytics
- Point-in-time restore
- Custom data residency
- Additional sandbox environments

### Process

1. **Review Requirements**
   - Check storage usage: Settings > Usage
   - Verify API usage: Settings > API
   - Confirm team size: Settings > Team

2. **Prepare for Downgrade**
   - Complete pre-downgrade checklist
   - Export any Enterprise-only data
   - Download audit logs if needed

3. **Request Downgrade**
   - Contact support: support@acmecloud.com
   - Include customer ID
   - Confirm you've completed checklist
   - Downgrades processed within 48 business hours

4. **Post-Downgrade**
   - Verify Basic tier limits are respected
   - Reconfigure authentication (SSO users)
   - Update API integration if needed

### Billing

- Credit for unused Enterprise time applied to next bill
- Basic tier charges begin on next billing cycle
- No refunds for partial months

### Downgrade Restrictions

You cannot downgrade if:
- Outstanding balance on account
- Active Premium SLA subscription
- Custom contract terms in place
- Currently in trial period

## Trial to Paid Conversion

### Basic Tier
- Automatic conversion at trial end
- Credit card required before trial expires
- Seamless transition, no data migration

### Enterprise Tier
- Contact sales during trial
- Custom contract available
- Optional: add Premium SLA

## Questions?

Contact our sales team at sales@acmecloud.com for migration assistance.
