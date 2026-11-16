"""Environment-driven settings."""

import os
from pathlib import Path

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
# Overridable because TASK.md allows a different OpenAI-compatible provider.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-oss-20b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nvidia/nemotron-3-embed-1b")
MCP_URL = os.getenv("MCP_URL", "http://localhost:8002")


def corpus_dir() -> Path:
    """CORPUS_DIR if set; else ../corpus (local run) or ./corpus (docker mount)."""
    configured = os.getenv("CORPUS_DIR")
    if configured:
        return Path(configured)
    here = Path(__file__).resolve().parent
    for candidate in (here.parent / "corpus", here / "corpus"):
        if candidate.is_dir():
            return candidate
    return here.parent / "corpus"
