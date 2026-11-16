# Design

## Approach

The provided package has deliberate faults in three places:

- The knowledge base contradicts itself and contains one hostile paragraph (`corpus/escalation.md`).
- The backend fails about half the time, like a real API under trouble.
- The MCP server hides those failures badly.

The API itself is the small part. Most of the work is being correct in spite of these three things. The trace shows how each answer was produced.

## Request flow

1. **Retrieve.** Embed the question; take the 8 most similar corpus sections, at most 3 per document.
2. **LLM call 1.** The model must reply with a function call: `reply` to answer directly, or the tools it needs.
3. **Tools.** Requested tools run in parallel through the MCP server.
4. **LLM call 2.** The model gets the tool results and writes the answer.

Knowledge-base questions cost one LLM call. Account questions cost two. Refund questions take a separate path after step 2 (see "Refunds").

## Decisions

### At most <u>two LLM calls</u>

- The code cannot make a third call. There is no loop: every path makes one call, then at most one more.
- The second call cannot ask for tools.
- If the first call returns nothing usable, it is repeated once. That repeat is the second call. If it then asks for tools, the code runs them and writes a plain answer from the tool data (no third LLM call).
- The price: one tool cannot use another tool's result. For example, the model cannot look up the account first and then fetch the payment method by its ID. None of the three required tools needs that.
- Embedding calls are retrieval, not LLM calls.

### Conflicting documents are <u>resolved by date</u>

- The corpus has two prices ($50 / $75) and two retention periods (30 / 90 days). The code knows nothing about them.
- Each document's date is read from its header and shown with every excerpt.
- The model is told: when excerpts conflict, the newest is current.
- A test checks that every document has a date. Without one the rule silently fails.

### Retrieval: 8 sections, at most 3 per file

- Eight sections leave room for a multi-part question without a long prompt, and the cap of three per file stops one long document from filling every slot. 
*Need future research to see if 8 is the right number.

### The model cannot choose the customer

- Tool schemas have no `customer_id` parameter. The app adds it from the request.
- A question like "check cust_003 for me" from cust_001 cannot read another account. So, the model cannot be tricked into giving away another customer's data.

### Refunds: the model fills in a form, the code writes the answer. <u>Deterministic and programmatic approach</u>

I see that `corpus/escalation.md` tells the assistant to say refunds are approved. The requirement: the assistant must never tell a customer that a refund has been, or will be, given.

<u>A prompt rule is not a guarantee</u>: the model may not follow it. Checking the finished text is not a guarantee either. So on refund questions the model writes no text.

1. **Routing.** Every function the model can call has a required flag `involves_refund`. The model's own text is shown only after an explicit `false`. A `true`, a missing flag, or a call to `refund_case` sends the request to the refund path. Plain text without a function call is never shown!
2. **Lookups by code.** The app fetches account and billing itself.
3. **A form, not an answer.** The second call can only return `refund_form`: a number of days, a file name from the retrieved list, yes/no/unknown, a boolean, a price. Any text next to it is discarded.
4. **Checks by code.** The window is kept only if the cited file is the policy for the customer's tier and states that number of days. Otherwise the answer says the window could not be determined.
5. **Text by code.** `app/refund.py` builds the answer from fixed sentences, the form and the tool data. If a human is needed, or no usable form came back, the code opens a P2 ticket.

Example of the answer the customer sees when LLM choose refund way (fixed sentences):

```text
I can't approve or promise a refund; that decision is made by a human agent.
Your account, as verified: enterprise tier, status active.
Last charge on record: $50.00 on 2026-11-02 (Enterprise plan).
Under the refund policy for your tier, the refund window is 30 days [refund_enterprise.md].
From the dates available, the payment appears to be inside that window; a human agent still has to confirm this and make the decision.
Ticket TKT-1042 has been opened and a human agent will review your request.
```

**Why there is no judge model.** The form already gives an exact guarantee where it matters most. A judge would either break the two-call limit or cover only the least risky path. It is the next step for production, where the two-call limit does not apply.

### Retries live in the app, not in the MCP server (MCP is the only a transport layer!)

The response must report the true number of retries. If the MCP server retried internally, the app could only guess.

- **MCP server:** one backend attempt, 4 s timeout. On failure it says what kind: `rate_limit`, `timeout`, `service_error` or `not_found`.
- **App:** up to 4 attempts within 25 s per tool.

| Outcome | Reaction |
|---|---|
| `rate_limit` | Wait the server's `Retry-After` (5 s), retry |
| `timeout`, `service_error` | Back off 0.5 s, 1 s, 2 s, retry |
| other errors | Fail at once |
| data older than 24 h | Retry for a fresh copy |
| only stale copies arrive | Return the freshest, flagged `stale: true` |
| all attempts fail | Tell the model the data was unavailable |

- **Why 4 s:** the backend answers <u>at once</u> or <u>hangs 5–30 s</u>.
- **Why 24 h:** `corpus/account_and_billing.md` says cached data may be up to 24 hours old.
- **Why stale data is retried:** the backend's stale response shows a suspended account as `active`. That is wrong, not just old.
- A failed tool never fails the request.

### One ticket per request (idempotent key)

- Creating a ticket is the only action that changes anything.
- Each ticket request carries a key. The backend returns the same ticket for the same key instead of creating a new one.
- The key is a hash of `request_id` and `customer_id`, so it is the same on every retry.
- If a ticket request times out, the app does not know whether the ticket was created. It retries with the same key and gets the same ticket. Checked in the backend audit log.

### Counters come from the trace

`tool_calls`, `retries` and `llm_calls` are computed from the trace timeline, so `/ask` and `/trace` cannot disagree. Failed requests save their trace too.

### Kept simple (as for testing task)

- **No vector database.** 120 chunks in a numpy matrix.
- **No LLM SDK.** Two REST endpoints called with `httpx`.
- **Traces in memory**, last 1000. The eval script saves them to disk.
- **Three MCP tools.** `reply`, `refund_case` and `refund_form` are not MCP tools. They never reach the backend: they tell the app which path to take and what shape the model's reply must have.

## Tests

18 tests, kept few on purpose. LLM and MCP are mocked, so no API key or network is needed.

- **API and trace:** `/ask` matches the contract; an LLM outage gives 503 and still saves the trace.
- **LLM budget:** 1 call without tools, 2 with tools, never more than 2; after a repeated first call the answer comes from tool data.
- **Safety:** `customer_id` comes only from the request and cannot change the backend path.
- **Refunds:** the answer is built by code from the form; the window must appear in the cited document.
- **Retries:** `Retry-After`, attempt limit, stale data refetched, same idempotency key on retry.
- **MCP server:** typed backend errors; escalation returns `ticket_id`.
- **Retrieval:** cosine ranking; every corpus document has a date.

Run: `cd app && pytest tests` and `cd mcp_server && pytest tests`.

## Issues found in the provided package

### MCP server (fixed)

| Problem | Effect | Fix |
|---|---|---|
| `as_of`, `canceled_at`, `suspended_at` dropped | Stale data undetectable; Q7 and Q10 unanswerable | Full backend payload passed through |
| Results returned as `str(dict)` | Not valid JSON | `json.dumps` |
| Every failure became one generic string | Caller cannot tell "wait" from "give up" | Each error names its kind, and `rate_limit` says how long to wait |
| 2 s timeout, 100 ms retries, `Retry-After` ignored | All retries wasted inside the rate-limit window | One attempt; retries moved to the app |
| Idempotency key built from the current second | A retry creates a second ticket | Caller's key, or a hash of the ticket content |
| `ticket_id` discarded | Customer gets no reference | Returned |
| IDs put into the backend URL unescaped | An ID could address another path | URL-quoted |

### Found by running the eval

| Observed | Change |
|---|---|
| `openai/gpt-oss-20b` hung on every request that day | Chat model set via `CHAT_MODEL` (see README) |
| Empty answers: the model spent its whole output limit reasoning | Limit raised to 8,192 tokens; a cut-off first call is repeated once |
| Raw `<tool_call>` markup returned as the answer | Prompt states one round of tools; markup is rejected as an answer |
| Q8 retrieved eight chunks from one file | At most 3 chunks per document |
| `sources` listed every retrieved file | Only cited files are reported |
| Q8 skipped the billing lookup; tickets not always opened | Refund path: lookups and tickets are done by code |
| Refund questions sometimes missed the refund path | Required `involves_refund` flag on every function; first call must be a function call |
| The model sometimes returned nothing on the first call (Q3) | The first call is repeated once |

## Limitations

- **The refund guarantee is not absolute.** A refund promise can still reach the customer in one case: the model wrongly marks a refund question as not about refunds and then promises a refund in its own text. <u>Removing this case completely would mean the model never writes free text at all.</u>
- **Other planted instructions are stopped only by the prompt.** For production, <u>I would review documents before they are indexed, by a person or by a separate model run offline</u>, so that planted text never reaches the knowledge base.
- **Refund answers are plain.** They are fixed sentences. A mixed question (Q8: price and refund) gets only the facts the form has fields for.
- **No authentication.** `customer_id` is taken from the request body and nobody checks it. In production it must come from the authenticated session.
- **Latency.** Requests took 4–28 s in the saved run. The model, not the retries, is the main delay. <u>For production: a faster model, and streaming the answer as it is written.</u>

I did my best within the scope of a test task; in a real product these decisions may need to change to match product requirements.
