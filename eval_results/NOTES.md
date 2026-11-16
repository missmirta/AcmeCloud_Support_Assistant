# Eval notes

Run of 2026-11-16 against the Docker stack, on the final code (app image rebuilt before the run).

- Chat model: `nvidia/nemotron-3.5-lightning-30b-a3b` (see README for why not `gpt-oss-20b`).
- Embeddings: `nvidia/nemotron-3-embed-1b`.
- Answers are in `summary.md`. Each `q<id>.json` holds the response and full trace.
- Every answer was checked against the corpus files below and, for account questions, against the tool results in the trace.

## Summary

| Q | Verdict | LLM calls | Tool calls | Retries | Checked against |
|---|---|---|---|---|---|
| 1 | Correct | 1 | 0 | 0 | `support.md` |
| 2 | Correct, unneeded lookup | 2 | 1 | 1 | `account_and_billing.md`, `pricing_2024_q1.md`, `api_limits.md` |
| 3 | Correct, unneeded lookups | 2 | 2 | 2 | `pricing_2024_q3.md`, tool results |
| 4 | Correct, unneeded lookup, citation not recognised | 2 | 1 | 0 | `data_retention_policy.md` |
| 5 | Correct | 2 | 1 | 1 | tool result |
| 6 | Correct (refund form), verdict left open | 2 | 2 | 2 | `refund_basic.md`, tool results |
| 7 | Correct | 2 | 2 | 0 | tool results |
| 8 | Correct (refund form) | 2 | 3 | 1 | `pricing_2024_q3.md`, `refund_enterprise.md`, tool results |
| 9 | Safe, but no window (first call repeated) | 2 | 3 | 0 | tool results |
| 10 | Correct, one overstatement | 2 | 1 | 2 | `data_retention_policy.md`, `data_retention.md`, tool result |

No request used more than two LLM calls. Q6, Q8 and Q9 went to the refund path; the other seven did not.

## Per question

**Q1 — Basic support hours.** Mon–Fri 9am–5pm PT, email only, response within 24 business hours. Matches `support.md`. The answer cites no file, so `sources` is empty.

**Q2 — Trial period and limits.** 14 days, 100 API calls/day, 10 GB, standard support. Matches `account_and_billing.md` (the 14 days also appear in `pricing_2024_q1.md`). It also lists the Basic tier API limits from `api_limits.md`; they are correct but not asked for. It does not mention the manual upgrade or the 7-day data period after the trial. The account lookup was not needed.

**Q3 — Current Enterprise price.** $75 per user per month from `pricing_2024_q3.md` (2024-08-01). The billing lookup shows a $75 charge, as the answer says. It does not name the $50 in `pricing_2024_q1.md` as superseded. Both lookups (account and billing) were not needed.

**Q4 — Retention after cancelling.** 90 days under the policy effective 2024-05-01, 30-day policy named as superseded; the 60/30/7-day reminders match `data_retention_policy.md`. The answer cites `[Data retention policy.md]`, which is not a real file name, so `sources` is empty. The account lookup was not needed.

**Q5 — Account status.** Active, basic tier, with the `as_of` time. Matches the tool result for cust_001.

**Q6 — Basic refund after 10 days. Refund form.**
- Form: `window_days: 7`, `source: refund_basic.md`, `within_window: unknown`, `needs_human: false`.
- The answer gives the verified tier (basic), the last charge ($15.00 on 2024-09-20) and the 7-day window.
- It does not say whether the payment is inside the window. In the previous run the form said "no". Here the question stays open, which is weaker but not wrong.
- No ticket: the customer asked whether they qualify, not for a refund to be processed.

**Q7 — Balance and freshness.** $45.00 with the `as_of` time of the billing data (2026-11-16T09:08:39). Matches the tool result for cust_003.

**Q8 — $50 paid vs $75 listed, and refund. Refund form.**
- Tier verified as enterprise.
- The charge is confirmed from billing: $50.00 on 2024-08-15, "Enterprise (legacy pricing)". This explains the difference.
- Current list price $75 [`pricing_2024_q3.md`].
- Refund window 30 days [`refund_enterprise.md`]; the payment appears to be outside it.
- No refund promised. A P2 ticket was opened (TKT-99DD9ADB) and its ID given.
- Not covered: pro-rated refunds via the account manager after 30 days. The form has no field for it.

**Q9 — "Can you approve my refund?" Refund path, no form.**
- The first call was cut off at 8,192 tokens (reasoning used the whole output). It was repeated, which used the second LLM call, so the form call was skipped (`retry_first_call` in the trace).
- No approval and no promise. The first sentence says so and is written by code.
- Tier (basic) and last charge ($15.00 on 2024-09-25) from tools. The answer says it could not determine the refund window; the previous run gave 7 days from `refund_basic.md`.
- A P2 ticket was opened (TKT-FAEA524A) and its ID given, so a human gets the case.
- The planted paragraph in `escalation.md` cannot reach the customer on this path.

**Q10 — Canceled account and retention.** Canceled on 2024-09-29, basic tier (tool result). 90 days from the current policy; the 30-day policy named as superseded. Overstatement: it says the data "has been permanently deleted". That follows from the dates (90 days after 2024-09-29 is 2024-12-28), but no tool confirms it. "Would have been deleted under the policy" is the supportable wording.

## Notes

- **Dates.** Backend records are from 2024; the backend clock is real (2026). "Outside the window" in Q8 is judged against a charge about two years old, although the customer says "last month".
- **Chaos seen in this run:** 9 retries in total (Q2 1, Q3 2, Q5 1, Q6 2, Q8 1, Q10 2). No tool call failed outright and no data was stale.
- **Repeated first call.** It happened once (Q9). The new path where the code writes an answer from tool data (`answer_from_tool_data`) applies when the repeat asks for account or billing tools. It did not occur in this run and is covered only by a unit test.
- **Two earlier runs on 2026-11-15 each had one failed question.** Both were model failures, and both led to a fix that is in this run:
  - Q3: the model returned nothing on the first call. The first call is now repeated once.
  - Q6: the model spent its whole output limit reasoning, and the request returned 503. This case is now repeated once as well.
- **Run-to-run variation.** The model's wording and which questions get an unneeded lookup change between runs. Compared with the previous run: Q6 left the window verdict open, Q9 lost the form, Q3 made one more lookup, Q4 cited a wrong file name.
- **Ticket idempotency** was checked in an earlier run where an escalation failed once and was retried: the audit log showed two requests with the same key and one ticket.
