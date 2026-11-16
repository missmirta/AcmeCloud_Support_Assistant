# AcmeCloud Support Assistant - Take-Home Task

## Overview

Build a FastAPI-based AI assistant that helps AcmeCloud employees answer customer questions by combining retrieval over an internal knowledge base with calls to backend services.

## What You're Building

An AI assistant that:
1. Retrieves relevant information from the internal knowledge base
2. Calls backend tools to check account status, billing, and create support tickets
3. Synthesizes accurate answers using an LLM
4. Tracks all operations for observability

## What's Provided

- **Corpus** (`corpus/`): Internal knowledge base documents
- **Backend** (`backend/`): Upstream services (account, billing, ticketing) — **do not modify this**
- **MCP Server** (`mcp_server/`): Tool interface to backend services
- **App Skeleton** (`app/`): FastAPI structure with API contract
- **Docker Compose**: Service orchestration
- **Eval Questions** (`eval/questions.json`): Test questions for your system

## Requirements

### API Contract

Implement these endpoints (see `app/models.py` for exact schema):

**`POST /ask`**
```json
Request: {
  "question": "What's my refund policy?",
  "customer_id": "cust_001"
}

Response: {
  "answer": "...",
  "request_id": "...",
  "sources": ["doc1.md", "doc2.md"],
  "tool_calls": 1,
  "retries": 0,
  "llm_calls": 2
}
```

**`GET /trace/{request_id}`**  
Return detailed trace of operations (retrieval, tool calls, LLM calls)

**`GET /health`**  
Return service health status

### Constraints

- **LLM Budget**: Design for 1-2 LLM calls per question
- **Corpus**: Load from `../corpus/`, implement retrieval
- **Tools**: Use provided MCP server at `MCP_URL` for:
  - `get_account_status(customer_id)`
  - `get_billing_history(customer_id)`
  - `escalate_to_human(customer_id, issue, priority)`

## LLM Provider

Use NVIDIA NIM free tier (https://build.nvidia.com):
- Chat: `openai/gpt-oss-20b`
- Embeddings: `nvidia/nemotron-3-embed-1b`
- API: OpenAI-compatible
- Add `NVIDIA_API_KEY` to `.env`

You may use a different provider if needed—document your choice in `README.md`.

## Testing

Run all 10 evaluation questions from `eval/questions.json` and save your results.

## What to Submit

1. **Code**:
   - Completed `app/` implementation
   - Modified `mcp_server/` (if you made changes)
   - Updated `docker-compose.yml` (if needed)
   - `.env.example`

2. **Documentation**:
   - `README.md`: Setup instructions and architecture
   - `DESIGN.md`: Your approach, design decisions, and any issues you encountered
   
3. **Results**: For each eval question:
   - Your answers
   - Saved traces
   - Notes on correctness and which documents you verified against

4. **Tests**: Tests for the parts you consider important

## Rules

- ❌ Do not modify `backend/` — it simulates upstream systems
- ❌ Do not modify `eval/questions.json`
- ❌ Do not hard-code answers from the knowledge base
- ✅ You may modify any other files
- ✅ You may add any Python libraries you need
- ✅ You may restructure `app/` however you like

Good luck!
