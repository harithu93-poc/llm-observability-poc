# LLM Observability POC

A self-hosted LLM serving platform with full production-style observability — built as a
platform-engineering take on an AI project. Two locally-hosted models (Llama 3.2, Phi-4) served
behind a FastAPI wrapper, instrumented end-to-end with the ELK stack.

**[Read the full comparison report →](docs/report.md)** · **[View the HTML report →](docs/report.html)**

## What this is

Most "AI portfolio projects" are thin wrappers around a chat API. This one treats a self-hosted
LLM the way a platform engineer treats any production service: containerized, logged, monitored,
alerted on, and load tested — with a real hardware-constrained finding to show for it (see the
report).

## Architecture

```
k6 load test ──▶ FastAPI wrapper (Docker) ──▶ Ollama (native, WSL2 host)
                       │
                       ▼
                 app.log (JSON lines)
                       │
                       ▼
                   Logstash ──▶ Elasticsearch ──▶ Kibana (dashboards + alerting)
```

## Stack

| Layer | Tech |
|---|---|
| Serving | Ollama (Llama 3.2 3B, Phi-4 14B) |
| API | FastAPI, containerized |
| Log shipping | Logstash |
| Storage / search | Elasticsearch |
| Dashboards / alerting | Kibana |
| Load testing | k6 |
| CI | GitHub Actions (lint, test, Docker build) |

## Repo structure

```
├── app/                 FastAPI wrapper + Dockerfile
├── tests/                pytest smoke tests
├── logstash/pipeline/     Logstash config
├── load-test/             k6 load test script
├── scripts/                Elasticsearch stats query
├── docs/                    report.md, report.html, build-log.md, plan.md
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Running it

```bash
# prerequisites: WSL2, Docker Desktop with WSL integration, Ollama installed natively
ollama pull llama3.2
ollama pull phi4

git clone <this repo>
cd llm-observability-poc
echo "KIBANA_ENCRYPTION_KEY=$(openssl rand -hex 32)" > .env

docker compose up -d
```

Then:
- API: `http://localhost:8000/chat` (POST `{"prompt": "...", "model": "llama3.2"}`)
- Kibana: `http://localhost:5601`
- Elasticsearch: `http://localhost:9200`

Load test: `k6 run load-test/chat-load-test.js`

## Key finding

Phi-4 (14B) measured **27.8s at 3.4 tokens/sec** on a 4GB VRAM GPU — a clear VRAM-ceiling
signal (CPU fallback), while Llama 3.2 (3B) stayed fast and GPU-accelerated. Full reasoning in
the [report](docs/report.md).

## Docs

- [`docs/plan.md`](docs/plan.md) — original 3-week project plan
- [`docs/report.md`](docs/report.md) — full comparison report
- [`docs/report.html`](docs/report.html) — visual version of the report
- [`docs/build-log.md`](docs/build-log.md) — detailed day-by-day build log, decisions, and gotchas
