"""
FastAPI wrapper around Ollama for the LLM Observability POC.

Every /chat request is timed and logged as a single structured JSON line
to logs/app.log — this is what Logstash will ingest in Week 2.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

ALLOWED_MODELS = {"llama3.2", "phi4"}

# ---------------------------------------------------------------------------
# Structured JSON logger — one line per request, no extra formatting.
# ---------------------------------------------------------------------------
logger = logging.getLogger("llm_wrapper")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(LOG_FILE)
handler.setFormatter(logging.Formatter("%(message)s"))  # raw JSON only, no prefix
logger.addHandler(handler)
logger.propagate = False


def log_request(record: dict):
    """Write a single structured JSON line."""
    logger.info(json.dumps(record))


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="LLM Observability POC Wrapper")


class ChatRequest(BaseModel):
    prompt: str
    model: str = "llama3.2"


class ChatResponse(BaseModel):
    response: str
    model: str
    latency_ms: float
    tokens_generated: int | None = None
    tokens_per_second: float | None = None


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if req.model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"model must be one of {ALLOWED_MODELS}")

    start = time.perf_counter()
    start_iso = datetime.now(timezone.utc).isoformat()
    status = "success"
    error_message = None
    response_text = ""
    tokens_generated = None
    tokens_per_second = None

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": req.model, "prompt": req.prompt, "stream": False},
            )
            r.raise_for_status()
            data = r.json()

        response_text = data.get("response", "")
        # Ollama returns eval_count (tokens generated) and eval_duration (ns) when stream=False
        eval_count = data.get("eval_count")
        eval_duration_ns = data.get("eval_duration")
        if eval_count and eval_duration_ns:
            tokens_generated = eval_count
            tokens_per_second = round(eval_count / (eval_duration_ns / 1e9), 2)

    except httpx.HTTPStatusError as e:
        status = "error"
        error_message = f"ollama returned {e.response.status_code}"
    except httpx.RequestError as e:
        status = "error"
        error_message = f"could not reach ollama: {e}"
    finally:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        log_request({
            "timestamp": start_iso,
            "model": req.model,
            "prompt_length": len(req.prompt),
            "response_length": len(response_text),
            "latency_ms": latency_ms,
            "tokens_generated": tokens_generated,
            "tokens_per_second": tokens_per_second,
            "status": status,
            "error_message": error_message,
        })

    if status == "error":
        raise HTTPException(status_code=502, detail=error_message)

    return ChatResponse(
        response=response_text,
        model=req.model,
        latency_ms=latency_ms,
        tokens_generated=tokens_generated,
        tokens_per_second=tokens_per_second,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
