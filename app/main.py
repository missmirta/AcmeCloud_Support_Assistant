"""
AcmeCloud Support Assistant.

POST /ask                 retrieve -> LLM -> (tools -> LLM), see assistant.py
GET  /trace/{request_id}  full timeline of a previous /ask
GET  /health              service status
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

import config
from assistant import Assistant
from llm import LLMClient, LLMCutOff, LLMError
from mcp_client import MCPClient
from models import AskRequest, AskResponse, Trace
from retrieval import CorpusIndex
from tracing import TraceRecorder, TraceStore

logger = logging.getLogger("acmecloud.app")


class Services:
    """Process-wide dependencies. The corpus index is built once, on first need."""

    def __init__(self):
        self.llm = LLMClient()
        self.mcp = MCPClient(config.MCP_URL)
        self.traces = TraceStore()
        self.index: CorpusIndex | None = None
        self._index_lock = asyncio.Lock()

    async def assistant(self) -> Assistant:
        async with self._index_lock:
            if self.index is None:
                self.index = await CorpusIndex.build(config.corpus_dir(), self.llm.embed)
        return Assistant(self.index, self.llm, self.mcp)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.services = Services()
    try:
        await app.state.services.assistant()
    except Exception as e:
        # Stay up: /health reports the problem and /ask retries the build.
        logger.error("Corpus index not built at startup: %s", e)
    yield
    await app.state.services.llm.aclose()
    await app.state.services.mcp.aclose()


app = FastAPI(title="AcmeCloud Support Assistant", lifespan=lifespan)


@app.get("/health")
async def health():
    """Health check endpoint."""
    services: Services = app.state.services
    index_ready = services.index is not None
    mcp_ok = await services.mcp.healthy()
    return {
        "status": "ok" if index_ready and mcp_ok else "degraded",
        "index_ready": index_ready,
        "chunks": len(services.index.chunks) if index_ready else 0,
        "mcp": "ok" if mcp_ok else "unreachable",
    }


@app.post("/ask")
async def ask(request: AskRequest) -> AskResponse:
    """Answer customer questions."""
    if not request.question.strip() or not request.customer_id.strip():
        raise HTTPException(status_code=400, detail="question and customer_id must not be empty")

    # Known weakness: customer_id is trusted as sent. There is no authentication,
    # so a caller can name any customer and read that account's data. In production
    # it must come from the authenticated session, not from the request body.

    services: Services = app.state.services
    trace = TraceRecorder(request.request_id or f"req_{uuid.uuid4().hex}", request.question, request.customer_id)
    try:
        assistant = await services.assistant()
        answer, sources = await assistant.answer(trace)
    except LLMCutOff as e:
        trace.add("llm_call", model=services.llm.chat_model, tokens=e.tokens, finish_reason="length",
                  purpose="cut_off")
        answer, sources = await assistant.hand_off(trace)
    except LLMError as e:
        trace.add("decision", action="failed", reason=str(e))
        raise HTTPException(status_code=503, detail=f"{e} (request_id={trace.request_id})")
    finally:
        # Failed requests keep their trace too - that is when it matters most.
        services.traces.put(trace.to_trace())

    return AskResponse(
        answer=answer,
        request_id=trace.request_id,
        sources=sources,
        tool_calls=trace.tool_calls,
        retries=trace.retries,
        llm_calls=trace.llm_calls,
    )


@app.get("/trace/{request_id}")
async def get_trace(request_id: str) -> Trace:
    """Get trace for a specific request."""
    trace = app.state.services.traces.get(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"No trace for request_id {request_id}")
    return trace


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
