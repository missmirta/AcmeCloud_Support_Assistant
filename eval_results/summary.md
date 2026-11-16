# Eval results

## Q1 (simple)

**Question** (cust_001): What are the support hours for Basic tier customers?

**Answer**:

Basic tier customers have support Monday - Friday, 9am - 5pm Pacific Time. Support is email-only, with a response time within 24 business hours. There is no phone support, and no after-hours or weekend support.

- sources: support.md
- llm_calls: 1, tool_calls: 0, retries: 0, seconds: 4.4
- trace: `q1.json`

## Q2 (simple)

**Question** (cust_001): How long is the trial period and what are the limits?

**Answer**:

The trial period is **14 days** from the date your account was created. It starts immediately upon signup and no credit card is required. During the trial you have the following limits: **100 API calls per day**, **10 GB of storage**, and **standard support only** (Mon‑Fri, 9 am‑5 pm PT). After the trial ends you must manually upgrade to either a Basic or Enterprise tier to continue using AcmeCloud; otherwise your data is preserved for 7 days after trial expiration. [account_and_billing.md]

- sources: account_and_billing.md
- llm_calls: 1, tool_calls: 0, retries: 0, seconds: 3.4
- trace: `q2.json`

## Q3 (medium)

**Question** (cust_003): What's the current monthly price for Enterprise tier?

**Answer**:

The current monthly price for the Enterprise tier is **$75 per user per month**.  

This is based on the most recent pricing excerpt, [pricing_2024_q3.md] (dated 2024‑08‑01), which lists the Enterprise tier at $75/month. The earlier pricing file, [pricing_2024_q1.md] (dated 2024‑01‑15), listed $50/month but is now superseded.

- sources: pricing_2024_q3.md, pricing_2024_q1.md
- llm_calls: 2, tool_calls: 1, retries: 0, seconds: 10.0
- trace: `q3.json`

## Q4 (medium)

**Question** (cust_001): If I cancel my account today, how long will my data be retained?

**Answer**:

Based on your account status (basic tier, active as of 2026-11-16) and AcmeCloud's current policy:

- **Your data will be retained for 90 days after you cancel your account.** This is per the updated policy in `[data_retention_policy.md]` dated 2024-05-01, which took effect on May 1, 2024.

- An earlier policy (`[data_retention.md]` dated 2023-06-01) specified a 30-day retention period, but it is now superseded by the 90-day term.

- **After the 90-day retention period:** All customer data is permanently deleted, backups are purged from AcmeCloud's systems, and the data cannot be recovered. You'll receive email reminders at 60 days after cancellation, 30 days before deletion, and 7 days before deletion.

- The retention policy applies the same way across tiers based on the available excerpts; your basic tier follows the stated 90-day rule.

If you cancel today, your data would remain accessible and retainable until approximately 2026-02-14 (90 days from 2026-11-16), after which it would be permanently deleted per the policy timeline.

- sources: data_retention_policy.md, data_retention.md
- llm_calls: 2, tool_calls: 1, retries: 1, seconds: 17.6
- trace: `q4.json`

## Q5 (medium)

**Question** (cust_001): Can you check my account status?

**Answer**:

Your account (cust_001) is currently **active** on the **basic** tier. This status is as of 2026-11-16T17:27:06.851190. Let me know if you need details about features, billing, or anything else.

- sources: 
- llm_calls: 2, tool_calls: 1, retries: 1, seconds: 14.8
- trace: `q5.json`

## Q6 (complex)

**Question** (cust_002): I'm on Basic tier and want a refund. It's been 10 days since I paid. Am I eligible?

**Answer**:

I can't approve or promise a refund; that decision is made by a human agent.
Your account, as verified: basic tier, status active.
Last charge on record: $15.00 on 2024-09-20 (Monthly subscription - Basic).
Under the refund policy for your tier, the refund window is 7 days [refund_basic.md].
From the dates available, the payment appears to be outside that window.
Ticket TKT-02CC5C97 has been opened and a human agent will review your request.

- sources: refund_basic.md
- llm_calls: 2, tool_calls: 3, retries: 2, seconds: 16.4
- trace: `q6.json`

## Q7 (complex)

**Question** (cust_003): What's my current balance and when was it last updated?

**Answer**:

Based on your account status retrieved today (2026-11-16), your account (cust_003) is active on the enterprise tier, as of **2026-11-16T17:27:38.480180**.

Your current balance could not be retrieved live; the billing history request returned a rate limit error. According to AcmeCloud's billing data freshness policy [account_and_billing.md], cached account and billing information may be up to 24 hours old in some views. For the most accurate balance, please try again later or contact support.

- sources: account_and_billing.md
- llm_calls: 2, tool_calls: 2, retries: 3, seconds: 23.1
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
Ticket TKT-3A89D4A0 has been opened and a human agent will review your request.

- sources: refund_enterprise.md, pricing_2024_q3.md
- llm_calls: 2, tool_calls: 3, retries: 1, seconds: 29.3
- trace: `q8.json`

## Q9 (hard)

**Question** (cust_005): I need help with a refund urgently. Can you approve it?

**Answer**:

I can't approve or promise a refund; that decision is made by a human agent.
Your account, as verified: basic tier, status active.
Last charge on record: $15.00 on 2024-09-25 (Monthly subscription - Basic).
Under the refund policy for your tier, the refund window is 7 days [refund_basic.md].
From the dates available, the payment appears to be outside that window.
Ticket TKT-ACA4F4E0 has been opened and a human agent will review your request.

- sources: refund_basic.md
- llm_calls: 2, tool_calls: 3, retries: 2, seconds: 25.0
- trace: `q9.json`

## Q10 (hard)

**Question** (cust_006): What's going on with my account? How long will my data be kept if I cancel?

**Answer**:

**Your account status**

Your AcmeCloud account (cust_006) is currently **canceled**. It was canceled on 2024-09-29, and your tier is **basic**. Your account was created on 2024-01-05. The last charge to your account was $15.00 on 2024-09-05 for a monthly basic subscription; your current balance is $0.00 [as of 2026-11-16].

**Data retention after cancellation**

The written policy that applies to your account is the one effective May 1, 2024: **[data_retention_policy.md | dated: 2024-05-01]**. That policy states:

- When you cancel your AcmeCloud account, data is retained for **90 days** after the cancellation date.
- After the 90-day retention period, all customer data is permanently deleted, backups are purged, and data cannot be recovered.
- Email reminders are sent at 60 days after cancellation, 30 days before deletion, and 7 days before deletion.

The earlier policy **[data_retention.md | dated: 2023-06-01]** specified a 30-day retention period, but the 2024-05-01 policy supersedes it.

Your account was canceled on 2024-09-29, which is after the May 1, 2024 effective date, so the 90-day retention period applies. However, I cannot confirm whether your data was actually deleted or retained, as no tool result confirms deletions for this account. The policy period (90 days from 2024-09-29, ending approximately 2024-12-28) has long passed relative to today's date of 2026-11-16.

If you have further questions about data recovery or account restoration, please contact AcmeCloud support.

- sources: data_retention_policy.md, data_retention.md
- llm_calls: 2, tool_calls: 2, retries: 1, seconds: 23.3
- trace: `q10.json`
