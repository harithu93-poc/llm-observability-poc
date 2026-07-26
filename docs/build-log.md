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

### [Week 1, Day 4] — Containerized the wrapper
- Decision: keep Ollama running **natively** in WSL2 (already had both models pulled; avoids
  re-pulling inside a container and avoids GPU passthrough config complexity for the 4GB VRAM
  Quadro T1000). Only the FastAPI wrapper is containerized.
- `app/main.py` updated: `OLLAMA_BASE_URL` now reads from env var (default `localhost:11434`
  for local runs, overridden to `http://host.docker.internal:11434` in compose).
- Added `app/Dockerfile` — python:3.11-slim base, installs requirements, runs uvicorn on :8000.
- Added `docker-compose.yml` at repo root — single `llm-wrapper` service for now, using
  `extra_hosts: host.docker.internal:host-gateway` to reach native Ollama from inside the
  container. Logs volume-mounted to `./app/logs` so they land on host filesystem (needed for
  Logstash to read them in Week 2). Structured with a comment noting ES/Logstash/Kibana
  services join this same file next week.
- Uncommented the `docker-build` job in CI — now runs alongside `lint-and-test` on every push.
- **Week 1: complete** (serving layer running end-to-end, containerized, tested, in CI).

### [Week 2, Day 8] — Elasticsearch + Kibana
- Added `elasticsearch` (single-node, security disabled for local POC, 512MB heap cap) and
  `kibana` services to `docker-compose.yml`. Used current stable version **9.4.4** for both
  (corrected from an initial stale 8.15.0 assumption — worth double-checking Elastic's current
  release before pinning versions, since it moves fast).
- WSL2 gotcha hit and resolved: Elasticsearch needs `vm.max_map_count=262144`, higher than the
  WSL2 default — set via `sudo sysctl -w vm.max_map_count=262144` and persisted in
  `/etc/sysctl.conf`.
- Verified: `curl localhost:9200/_cluster/health` → yellow (expected/normal for single-node,
  no replica shards to allocate). Kibana reachable at `localhost:5601`.

### [Week 2, Day 9-10] — Logstash pipeline
- Added `logstash` service + `logstash/pipeline/logstash.conf`: file input tailing
  `/logs/app.log` (JSON codec), date filter mapping the app's own `timestamp` field to
  `@timestamp` (not Logstash's ingest time), output to Elasticsearch with daily index pattern
  `llm-observability-YYYY.MM.dd`.
- `sincedb_path => /dev/null` used deliberately for POC (always re-reads from start on restart)
  — noted as a thing to change if this ever needs to run long-term.
- **Confirmed working end-to-end**: FastAPI → app.log → Logstash → Elasticsearch. Verified via
  `_cat/indices` and `_search` — documents landing with correct structured fields.
- **First real data point of note**: Phi-4 (14B) request took 27.8s at only 3.4 tokens/sec vs.
  Llama 3.2's much faster response — strong signal the 4GB VRAM Quadro T1000 can't fit Phi-4
  and it's falling back to CPU. Flagged as a key finding for the Week 3 comparison report —
  a genuine resource-constrained-environment observability story, not just a clean benchmark.

### [Week 2, Day 11-13] — Kibana dashboards (in progress)
- Data view created: `llm-observability` on pattern `llm-observability-*`, timestamp `@timestamp`.
- Building 5 panels: latency p50/p95 by model, tokens/sec by model, request volume over time,
  error rate, compute-time-per-model (cost proxy). Combining into "LLM Serving Overview" dashboard.
- **Dashboard complete** — all 5 panels built and working.

### [Week 3, Day 15-16] — Alerting
- Kibana Alerting required an encryption key (`xpack.encryptedSavedObjects.encryptionKey`) not
  set by default — added `XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY` env var to the `kibana`
  service in `docker-compose.yml`, value generated via `openssl rand -hex 32` and stored in a
  gitignored `.env` file (kept out of version control deliberately).
- Rule created: Elasticsearch query rule against `llm-observability-*`, threshold on error count
  over a time window.
- Connector/action list in this Kibana version only surfaced **Cases** and **Workflows** (no
  Server log connector visible) — skipped actions entirely; the rule's execution history alone
  is sufficient to prove the alerting mechanism works, no connector required.
- Triggered by stopping Ollama temporarily and sending failing requests; confirmed via
  Stack Management → Rules → execution history.

### [Week 3, Day 17-18] — Load testing
- Chose k6 over Locust (installed via Ubuntu apt repo in WSL2).
- `load-test/chat-load-test.js`: ramping stages (3 → 6 concurrent users), weighted 70/30 toward
  llama3.2 over phi4 given phi4's much higher per-request latency (~28s observed) on the
  VRAM-constrained GPU — avoids the whole test queueing behind phi4 alone.
- Plan: run test while watching the Kibana dashboard live (auto-refresh ~10s) to observe
  latency/error rate behavior under load in real time; note what degrades first.

### [Week 1, Day 2-3 cont.] — GitHub repo structure + CI pipeline
- Repo structure finalized:
  ```
  llm-observability-poc/
  ├── app/            (main.py, requirements.txt, logs/ [gitignored])
  ├── tests/          (test_health.py)
  ├── docs/           (plan.md — the week-by-week plan)
  ├── .github/workflows/ci.yml
  ├── .gitignore
  ├── requirements-dev.txt
  └── README.md       (this file)
  ```
- Added `tests/test_health.py` — smoke tests for `/health` and `/chat` model validation,
  deliberately not dependent on a live Ollama instance so CI stays green without infra.
- GitHub Actions workflow (`.github/workflows/ci.yml`): lints with `ruff`, runs `pytest` on
  every push/PR to `main`. Docker build job stubbed in (commented out) to activate once
  `app/Dockerfile` exists on Day 4.
- Pushed to GitHub, CI pipeline confirmed running under repo's Actions tab.
