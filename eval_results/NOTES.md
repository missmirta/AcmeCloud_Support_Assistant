# Eval notes

Final run, 2026-11-16, against the Docker stack built from the final code. Every question returned HTTP 200.

- Chat model: `nvidia/nemotron-3.5-lightning-30b-a3b` (see README for why not `gpt-oss-20b`).
- Embeddings: `nvidia/nemotron-3-embed-1b`.
- Answers are in `summary.md`. Each `q<id>.json` holds the response and full trace.
- Each answer was checked against the corpus files below and, for account questions, against the tool results in the trace.

## Summary

| Q | Verdict | LLM calls | Tool calls | Retries | Checked against |
|---|---|---|---|---|---|
| 1 | Correct | 1 | 0 | 0 | `support.md` |
| 2 | Correct, unneeded lookup not made | 1 | 0 | 0 | `account_and_billing.md` |
| 3 | Correct, unneeded lookup | 2 | 1 | 0 | `pricing_2024_q3.md`, `pricing_2024_q1.md` |
| 4 | Correct, unneeded lookup | 2 | 1 | 1 | `data_retention_policy.md`, `data_retention.md` |
| 5 | Correct | 2 | 1 | 1 | tool result |
| 6 | Correct (refund form), ticket opened | 2 | 3 | 2 | `refund_basic.md`, tool results |
| 7 | Honest partial answer: billing rate-limited | 2 | 2 | 3 | tool results (account only) |
| 8 | Correct (refund form), ticket opened | 2 | 3 | 1 | `pricing_2024_q3.md`, `refund_enterprise.md`, tool results |
| 9 | Correct (refund form), ticket opened | 2 | 3 | 2 | `refund_basic.md`, tool results |
| 10 | Correct, deletion stated as unconfirmed | 2 | 2 | 1 | `data_retention_policy.md`, `data_retention.md`, tool results |

Totals: 11 retries, no request used more than two LLM calls, no output cut-offs, no stale data.

## Per question

**Q1 — Basic support hours.** Mon–Fri 9am–5pm PT, email only, no phone or weekend support. Matches `support.md`. Answered from the knowledge base in one LLM call, with no lookups.

**Q2 — Trial period and limits.** 14 days, 100 API calls per day, 10 GB, standard support, manual upgrade after the trial, data kept 7 days after expiry. Matches `account_and_billing.md`. The "no credit card" statement is also in that file. No lookup was needed.

**Q3 — Current Enterprise price.** $75 per user per month from `pricing_2024_q3.md` (dated 2024-08-01). It names the $50 price in `pricing_2024_q1.md` as superseded. One account lookup was made but not needed.

**Q4 — Retention after cancelling.** 90 days under the policy effective 2024-05-01. The 30-day policy in `data_retention.md` is named as superseded. The 60/30/7-day reminders match `data_retention_policy.md`. The answer cites the file, so `sources` lists it. One account lookup was made but not needed.

**Q5 — Account status.** Active, basic tier, with the `as_of` time. Matches the tool result for cust_001. One retry on the account lookup.

**Q6 — Basic refund after 10 days. Refund form.**
- Tier verified as basic. Last charge $15.00 on 2024-09-20 (tool result).
- Refund window 7 days [`refund_basic.md`]. Payment outside the window, judged from the charge record date.
- No refund promised. A P2 ticket was opened and its ID given.

**Q7 — Balance.** The account lookup succeeded: enterprise tier, active, with its `as_of` time. The billing lookup hit a rate limit on all 4 attempts, so the balance is not reported. The answer says so and cites the billing freshness policy. This is the backend's failure, handled as designed.

**Q8 — $50 paid vs $75 listed, and refund. Refund form.**
- Tier verified as enterprise. Charge confirmed from billing: $50.00 on 2024-08-15, "Enterprise (legacy pricing)". This explains the difference.
- Current list price $75 [`pricing_2024_q3.md`].
- Refund window 30 days [`refund_enterprise.md`]. The payment is 823 days before today, so it is outside the window. Before the fix the answer said "inside", because the model judged the date and the customer said "last month".
- No refund promised. A P2 ticket was opened and its ID given.
- Not covered: pro-rated refunds after 30 days. The form has no field for them.

**Q9 — "Can you approve my refund?" Refund form.**
- Tier (basic) and last charge ($15.00 on 2024-09-25) from tools.
- Payment outside the 7-day window. No approval, no promise. A P2 ticket was opened and its ID given.
- In an earlier run this request failed with a provider read timeout (503). This run had no failure.

**Q10 — Canceled account and retention.** Canceled on 2024-09-29, basic tier, from the tool result. The 90-day policy and the superseded 30-day policy are both named. The answer says it cannot confirm whether the data was deleted, since no tool reports deletions. It also says the policy period has passed, which is inference from the dates and is labelled as such.

## Notes

- **Dates.** Backend records are from 2024; the backend clock is real (2026). Refund windows are judged against the date of the last charge on record, not against what the customer says.
- **Cut-offs.** The output limit is now 16,384 tokens. The one cut-off seen during development (Q9, 8,192 tokens) is now recorded in the trace, with its token count and `finish_reason: length`, before the case is handed to a human.
- **Retries.** 11 in total: Q4 1, Q5 1, Q6 2, Q7 3, Q8 1, Q9 2, Q10 1. The only failure that reached the customer was the rate limit in Q7, and it was reported.
- **Run-to-run variation.** The model's wording and whether it makes an unneeded lookup change between runs (Q3, Q4 did in this run). Refund verdicts did not change between the last two runs.
- **Ticket idempotency** was checked in an earlier run where an escalation failed once and was retried: the audit log showed two requests with the same key and one ticket.
