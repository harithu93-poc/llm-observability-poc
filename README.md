# Self-Hosted LLM Serving Platform with ELK Observability

A platform-engineering take on an AI project: Ollama-served LLMs behind a FastAPI wrapper,
fully instrumented and monitored via the ELK stack.

## System Configuration

| Component | Spec |
|---|---|
| Device | Dell Precision 5540 |
| OS | Windows 11 |
| Processor | Intel Core i7-9850H @ 2.60GHz (6-core) |
| RAM | 64 GB |
| GPU | NVIDIA Quadro T1000 (4GB VRAM) + Intel UHD Graphics 630 (integrated) |
| Storage | 477 GB (314 GB free at project start) |

**Note:** GPU is VRAM-constrained (4GB) — Ollama will likely split inference between GPU/CPU
rather than fully offload. Track GPU vs CPU utilization in observability dashboards later as
an honest resource-constrained-environment data point.

## Models Selected

- **Llama 3.2 (3B)** — baseline, widely supported, strong community docs.
- **Phi-4** — Microsoft small model, different architecture/training approach, gives a genuine
  comparison point rather than "same thing twice."

Two models judged sufficient for the POC — model choice is secondary to proving the
observability pipeline works. Mistral 7B is a stretch-goal addition if time allows.

## Prerequisites / Environment Setup

### Why WSL2
Docker Desktop on Windows already runs Linux containers via WSL2 under the hood (Elasticsearch,
Kibana, Filebeat are all Linux images). Running the dev environment inside WSL2 directly avoids
Windows path/permission issues with volume mounts and file-watching (relevant for Filebeat).
GPU passthrough (CUDA) is supported inside WSL2 via NVIDIA's WSL-compatible driver.

### Setup steps (planned)
1. Install WSL2 with Ubuntu:
   ```powershell
   wsl --install -d Ubuntu
   ```
   (run from PowerShell as Administrator; reboot if prompted)
2. Install Docker Desktop for Windows.
3. Enable WSL2 integration for the Ubuntu distro:
   Docker Desktop → Settings → Resources → WSL Integration → enable Ubuntu.
4. Install NVIDIA's WSL-compatible GPU driver (from NVIDIA, not a separate WSL-specific package —
   the standard Windows driver with WSL support enabled).
5. Install Ollama **inside WSL2** (Linux install script), not the native Windows installer, to keep
   the whole stack (serving + observability) consistent inside one Linux environment.
6. Do all FastAPI/Python development inside WSL2 — treat it as the dev environment, Windows is
   just the host.

*(Exact commands for steps 2–5 to be filled in as they're run.)*

## Project Plan Summary

- **Week 1** — Serving layer: Ollama + FastAPI wrapper + Docker Compose, manual load test.
- **Week 2** — Observability layer: Elasticsearch + Kibana + Filebeat, dashboards.
- **Week 3** — Alerting, real load test, comparison write-up, README/portfolio polish.

Full day-by-day plan: see `llm-observability-poc-plan.md`.

---

## Log Shipping Decision

**Logstash chosen over Filebeat** for ingesting FastAPI wrapper logs into Elasticsearch —
prior working experience with Logstash. Pipeline: `app.log` (JSON lines) → Logstash → Elasticsearch.
(Original plan considered Filebeat-direct for a lighter footprint; swapped based on existing
skillset — faster to implement correctly, and Logstash leaves room for enrichment/filtering
later if needed.)

## Build Log

*(Steps get appended here chronologically as the project progresses — dates, commands run,
issues hit, fixes applied.)*

### [Setup] — WSL2 + Docker + Ollama decision made
- Confirmed hardware sufficient for both models without downgrading to quantized variants.
- Decided to develop inside WSL2 rather than native Windows for Docker/Filebeat consistency.

### [Week 1, Day 1] — Environment verified
- WSL2 (Ubuntu) installed and working.
- Docker Desktop installed; WSL Integration enabled via Settings → Resources → WSL Integration
  (required Docker Desktop engine to be fully started + "Use WSL2 based engine" checked under
  General before the Resources/WSL Integration tabs appeared).
- Ollama installed inside WSL2 via `curl -fsSL https://ollama.com/install.sh | sh`.
- Models pulled: `llama3.2` (3B, Meta) and `phi4` (14B, Microsoft) — kept as-is despite size
  mismatch; treated as a deliberate size-vs-efficiency comparison rather than apples-to-apples.
- Verified: `ollama run llama3.2 "hello, reply in one sentence"` → responded correctly.
- **Week 1 environment setup: complete.**

### [Week 1, Day 2-3] — FastAPI wrapper
- Project structure: `~/llm-observability-poc/app/` with Python venv.
- Built `main.py`: FastAPI wrapper around Ollama's `/api/generate` endpoint.
  - `POST /chat` — accepts `{prompt, model}`, restricted to `llama3.2` / `phi4` via `ALLOWED_MODELS`.
  - Captures per request: timestamp, model, prompt/response length, latency_ms, tokens_generated,
    tokens_per_second (derived from Ollama's `eval_count` / `eval_duration`), status, error_message.
  - Logs one structured JSON line per request to `app/logs/app.log` (dedicated logger, no prefix
    formatting) — this is the file Logstash will tail in Week 2.
  - `GET /health` endpoint added for basic liveness checks (useful later for container healthchecks).
- Dependencies: fastapi, uvicorn[standard], httpx, pydantic (requirements.txt pinned).
- Run locally: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`.
- Verified both success and error paths produce correctly shaped JSON log lines before moving on.
