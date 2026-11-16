# AcmeCloud Support Assistant

A FastAPI service that answers customer questions by combining retrieval over the internal knowledge base (`corpus/`) with live account tools (via the MCP server), using at most two LLM calls per question and recording a full trace of every request.

See [DESIGN.md](DESIGN.md) for the reasoning behind the design and the problems found in the provided package.

See [Generated_diagram_How_a_request_is_answered.pdf](Generated_diagram_How_a_request_is_answered.pdf) for a diagram of the request processing flow.

## Setup

Requirements: Docker with Compose. Python 3.11+ only for running tests and the eval script.

```bash
cp .env.example .env        # then put your NVIDIA NIM key in NVIDIA_API_KEY
docker compose up --build -d
curl localhost:8000/health  # {"status":"ok","index_ready":true,"chunks":120,"mcp":"ok"}
```

`status` is `degraded` when the corpus index could not be built (usually a bad API key) or the MCP server is unreachable; the other fields say which.

| Service | Port | Purpose |
|---|---|---|
| `app` | 8000 | The assistant (this submission) |
| `mcp_server` | 8002 | Tool interface to the backend (fixed, see DESIGN.md) |
| `backend` | 8001 | Simulated upstream systems (unmodified) |

### LLM provider

NVIDIA NIM, as suggested, with `nvidia/nemotron-3-embed-1b` for embeddings.

**Chat model deviation.** The eval script sets `CHAT_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b` to the working model, because `gpt-oss-20b` was not responding on NIM.
## API

```bash
curl -X POST localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"question": "Can you check my account status?", "customer_id": "cust_001"}'

curl localhost:8000/trace/<request_id>
```

`POST /ask` accepts an optional `request_id`; otherwise one is generated.

| Status | Meaning |
|---|---|
| 200 | Answer produced. Tool failures do not fail the request; the answer says the live data was unavailable. |
| 400 | Empty `question` or `customer_id` |
| 503 | LLM/embedding provider unavailable. The trace is still saved. |
| 404 | (`/trace`) unknown `request_id` |

## Architecture

```
POST /ask
   │
   ├─ 1. retrieve      embed question → cosine top-8 over corpus sections      (retrieval.py)
   │
   ├─ 2. LLM call 1    rules + dated excerpts + question + 3 tool schemas      (assistant.py, prompts.py)
   │        ├─ answers directly, via reply() ──────────────────► done (1 LLM call)
   │        └─ requests tools
   │
   ├─ 3. run tools     concurrently, via MCP, with retry policy                (mcp_client.py)
   │                   app ──► mcp_server ──► backend
   │
   └─ 4. LLM call 2    + tool results, tool_choice="none" ─────► done (2 LLM calls)

call 1 is always a function call carrying an involves_refund flag; refund questions branch after step 2:
   code looks up account + billing → LLM call 2 is forced to return a typed form
   → code writes the answer and opens a ticket if needed                         (refund.py)

every step → TraceRecorder → TraceStore → GET /trace/{request_id}             (tracing.py)
```

| File | Responsibility |
|---|---|
| `app/main.py` | Endpoints, startup, error mapping |
| `app/assistant.py` | The request flow; tool-call validation; LLM budget |
| `app/retrieval.py` | Corpus loading, section chunking, document dating, vector search |
| `app/prompts.py` | System rules, tool schemas, prompt assembly |
| `app/refund.py` | Refund questions: typed form filled in by the model, answer text written by code |
| `app/mcp_client.py` | Tool calls: retries, backoff, staleness, deadline |
| `app/llm.py` | Chat + embeddings over an OpenAI-compatible API |
| `app/tracing.py` | Timeline recording and trace storage |
| `mcp_server/` | One backend attempt per call, typed errors, full payload passthrough |

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest app/tests mcp_server/tests
```

No network or API key needed: the LLM, embeddings, MCP server and backend are faked.

## Evaluation

With the stack running:

```bash
python eval/run_eval.py
```

This runs the 10 questions in `eval/questions.json` and writes, to `eval_results/`:

- `q<id>.json` — the question, the response and the full trace
- `summary.md` — all answers with their counters

`eval_results/NOTES.md` holds the per-question correctness review and the corpus documents each answer was checked against.

The backend's failure sequence is seeded at startup, so `docker compose restart backend` replays the same failures and consecutive runs without a restart see different ones.
"# AcmeCloud_Support_Assistant" 
