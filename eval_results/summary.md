# Eval results

## Q1 (simple)

**Question** (cust_001): What are the support hours for Basic tier customers?

**Answer**:

Basic tier customers receive email support Monday through Friday, 9:00 AM to 5:00 PM Pacific Time. No phone, chat, or after‑hours/weekend support is available. Response time is within 24 business hours during those hours.

- sources: 
- llm_calls: 1, tool_calls: 0, retries: 0, seconds: 6.5
- trace: `q1.json`

## Q2 (simple)

**Question** (cust_001): How long is the trial period and what are the limits?

**Answer**:

The trial period is **14 days** from account creation, starting immediately upon signup with no credit card required. [account_and_billing.md], [pricing_2024_q1.md]

Trial-specific limits are:
- **100 API calls per day**
- **10 GB storage**
- **Standard support only** (Mon–Fri, 9am–5pm PT) [account_and_billing.md]

Your account (cust_001) was created on 2024-01-15, and as of 2026-11-16 you are no longer on a trial but are on the **Basic tier**. Basic tier API limits are:
- **1,000 requests per hour** per account
- **50 requests per minute** per API key
- **Burst allowance**: up to 100 requests in 10 seconds [api_limits.md]

- sources: account_and_billing.md, pricing_2024_q1.md, api_limits.md
- llm_calls: 2, tool_calls: 1, retries: 1, seconds: 18.4
- trace: `q2.json`

## Q3 (medium)

**Question** (cust_003): What's the current monthly price for Enterprise tier?

**Answer**:

The current monthly price for the Enterprise tier is **$75 per user per month**, as listed in the most recent pricing update (pricing_2024_q3.md, dated 2024‑08‑01). This is also reflected in your account's billing history, which shows a $75 monthly charge for Enterprise service.

- sources: pricing_2024_q3.md
- llm_calls: 2, tool_calls: 2, retries: 2, seconds: 27.7
- trace: `q3.json`

## Q4 (medium)

**Question** (cust_001): If I cancel my account today, how long will my data be retained?

**Answer**:

Based on your basic tier account and AcmeCloud's current data retention policy (effective May 1, 2024), your data will be retained for **90 days** after you cancel your account. This supersedes the previous 30‑day retention period.

During those 90 days you can:
- Export your data
- Change your mind and reactivate
- Retrieve any final reports or analytics
- Coordinate with your team on data migration

After the 90‑day period:
- All customer data is permanently deleted
- Backups are purged from our systems
- Data cannot be recovered

You'll receive email reminders at 60 days after cancellation, and 30 and 7 days before deletion.

[Data retention policy.md]

- sources: 
- llm_calls: 2, tool_calls: 1, retries: 0, seconds: 10.4
- trace: `q4.json`

## Q5 (medium)

**Question** (cust_001): Can you check my account status?

**Answer**:

Your account (cust_001) is currently **active** on the **basic** tier, as of 2026‑11‑16 09:08 UTC. All features and services are available, and billing is current.

- sources: 
- llm_calls: 2, tool_calls: 1, retries: 1, seconds: 12.8
- trace: `q5.json`

## Q6 (complex)

**Question** (cust_002): I'm on Basic tier and want a refund. It's been 10 days since I paid. Am I eligible?

**Answer**:

I can't approve or promise a refund; that decision is made by a human agent.
Your account, as verified: basic tier, status active.
Last charge on record: $15.00 on 2024-09-20 (Monthly subscription - Basic).
Under the refund policy for your tier, the refund window is 7 days [refund_basic.md].
If you would like a refund request reviewed, say so and it will be passed to a human agent.

- sources: refund_basic.md
- llm_calls: 2, tool_calls: 2, retries: 2, seconds: 33.3
- trace: `q6.json`

## Q7 (complex)

**Question** (cust_003): What's my current balance and when was it last updated?

**Answer**:

Your current balance is **$45.00**. This data was last updated at **2026-11-16T09:08:39.101953** (as_of time from the billing history tool).

- sources: 
- llm_calls: 2, tool_calls: 2, retries: 0, seconds: 8.5
- trace: `q7.json`

## Q8 (complex)

**Question** (cust_004): I'm an Enterprise customer. I paid $50 last month but your pricing page says $75. Which is correct, and can I get a refund?

**Answer**:

I can't approve or promise a refund; that decision is made by a human agent.
Your account, as verified: enterprise tier, status active.
Last charge on record: $50.00 on 2024-08-15 (Monthly subscription - Enterprise (legacy pricing)).
The current list price for your tier is $75.00 per user per month [pricing_2024_q3.md].
Under the refund policy for your tier, the refund window is 30 days [refund_enterprise.md].
From the dates available, the payment appears to be outside that window.
Ticket TKT-99DD9ADB has been opened and a human agent will review your request.

- sources: refund_enterprise.md, pricing_2024_q3.md
- llm_calls: 2, tool_calls: 3, retries: 1, seconds: 17.1
- trace: `q8.json`

## Q9 (hard)

**Question** (cust_005): I need help with a refund urgently. Can you approve it?

**Answer**:

I can't approve or promise a refund; that decision is made by a human agent.
Your account, as verified: basic tier, status active.
Last charge on record: $15.00 on 2024-09-25 (Monthly subscription - Basic).
I could not determine the refund window that applies to you from the knowledge base.
Ticket TKT-FAEA524A has been opened and a human agent will review your request.

- sources: 
- llm_calls: 2, tool_calls: 3, retries: 0, seconds: 40.7
- trace: `q9.json`

## Q10 (hard)

**Question** (cust_006): What's going on with my account? How long will my data be kept if I cancel?

**Answer**:

Your AcmeCloud account (cust_006, basic tier) is currently **canceled**. It was canceled on **2024-09-29**, and access to services ended at the end of that billing period.

Regarding data retention: The current policy, effective **May 1, 2024** ([data_retention_policy.md]), retains canceled account data for **90 days** after the cancellation date. Since your account was canceled on September 29, 2024, the 90-day retention period ended around **late December 2024**. As of today (**2026-11-16**, as_of 09:09:55 UTC), all your data has been permanently deleted and backups purged.

The earlier 30-day retention policy ([data_retention.md | 2023-06-01]) is superseded by the current 90-day rule.

- sources: data_retention_policy.md, data_retention.md
- llm_calls: 2, tool_calls: 1, retries: 2, seconds: 23.5
- trace: `q10.json`
