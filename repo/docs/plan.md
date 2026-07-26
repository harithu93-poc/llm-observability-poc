# Self-Hosted LLM Serving Platform with ELK Observability — POC Plan

**Goal:** Deploy Ollama-served LLMs behind an API, instrument every request, and build production-grade monitoring in ELK — a platform-engineering take on an AI project.

**Timeline:** 3 weeks, ~1–2 hrs/day (adjust to your pace — the plan is phase-based, not date-locked)

---

## Week 1 — Serving Layer

### Day 1 (today): Environment + Ollama running
- Install Docker + Docker Compose if not already set up.
- Install Ollama (native or containerized — native is simpler for GPU access if you have one).
- Pull 2 models to start: `ollama pull llama3.2` and `ollama pull phi4` (add `mistral` later if hardware allows).
- Sanity check: `ollama run llama3.2 "hello"` — confirm it responds.
- **End of day checkpoint:** Ollama serving locally on `localhost:11434`.

### Day 2–3: FastAPI wrapper
- Build a thin FastAPI service in front of Ollama's REST API (`/api/generate`).
- Endpoint: `POST /chat` — takes `{prompt, model}`, calls Ollama, returns response.
- Instrument the endpoint to capture, per request:
  - `start_time`, `end_time`, `latency_ms`
  - `time_to_first_token` (if streaming) — start simple with total latency if TTFT is fiddly at first
  - `tokens_generated`, `tokens_per_second`
  - `model_name`, `prompt_length`, `response_length`
  - `status` (success/error), `error_message` if any
- Log this as a **single structured JSON line per request** (not multi-line, not free text) — this is what Filebeat will ship.
- **End of day checkpoint:** hitting `/chat` produces one clean JSON log line with all the above fields.

### Day 4: Containerize
- Dockerfile for the FastAPI service.
- `docker-compose.yml` wiring: `ollama` service + `fastapi-wrapper` service, shared network, wrapper logs mounted to a volume (e.g., `./logs/app.log`).
- Confirm `docker compose up` gives you a working `/chat` endpoint end-to-end.
- **End of day checkpoint:** whole serving stack runs with one `docker compose up`.

### Day 5–6: Manual load test + baseline numbers
- Use `k6` or `locust` (whichever you're more comfortable with from your DevOps background) to fire ~50–100 requests at both models.
- Eyeball the raw logs — confirm latency/tokens-per-second numbers look sane and error handling works (try a bad prompt/model name to confirm the error path logs correctly).
- **End of day checkpoint:** you have a folder of real log data to build dashboards against — don't skip this, empty dashboards are hard to build well.

### Day 7: Buffer / catch-up
- Use this day to fix anything broken in Days 1–6 before moving to ELK. Don't start the ELK stack with a shaky serving layer — it makes debugging confusing (is it the app or the pipeline?).

---

## Week 2 — Observability Layer (ELK)

### Day 8: Elasticsearch + Kibana up
- Add `elasticsearch` and `kibana` services to `docker-compose.yml`.
- Single-node ES, limited heap for POC: `ES_JAVA_OPTS=-Xms512m -Xmx512m`.
- Confirm Kibana loads at `localhost:5601` and can reach Elasticsearch (Stack Management → check cluster health).
- **End of day checkpoint:** ELK stack (minus Filebeat) is up and green.

### Day 9–10: Filebeat → Elasticsearch
- Add `filebeat` service, mount it to read `./logs/app.log`.
- Configure Filebeat's `filebeat.yml`: input = your log file, output = Elasticsearch, since your app already logs clean JSON use the `json.keys_under_root: true` option so fields land as proper Elasticsearch fields (not a single blob).
- Run a few test requests, confirm documents land in Elasticsearch: check via Kibana Dev Tools (`GET /filebeat-*/_search`).
- **End of day checkpoint:** every `/chat` request appears as a structured document in Elasticsearch within seconds.

### Day 11–13: Kibana dashboards
Build these panels (this is your resume screenshot material):
- **Latency over time** — p50/p95 line chart, split by model.
- **Tokens/sec by model** — bar chart comparing your 2–3 models.
- **Request volume** — requests over time.
- **Error rate** — % failed requests, with a table of recent errors.
- **Cost proxy** — total compute time per model per day (self-hosted "cost" = time, since there's no per-token billing).
- Combine into a single Kibana dashboard: "LLM Serving Overview."
- **End of day checkpoint:** one dashboard, screenshot-worthy, all panels populated with real data.

### Day 14: Buffer / polish dashboards
- Clean up panel titles, add a text panel summarizing what the dashboard shows (useful for demoing later).

---

## Week 3 — Alerting, Load Testing, Write-up

### Day 15–16: Alerting
- Kibana Alerting rule: e.g., "latency p95 > 3000ms for 5 min" or "error rate > 10%."
- Wire it to something simple — a webhook to a Slack channel or even just a logged alert — the point is demonstrating you *can* wire alerting, not building a full pager pipeline.
- **End of day checkpoint:** trigger the alert intentionally (e.g., stop Ollama mid-test) and confirm it fires.

### Day 17–18: Real load test
- Run a heavier load test (k6/Locust, ramping concurrent users) against both models.
- Watch the Kibana dashboard live during the test — this is a great demo moment (screen-record it if you want a portfolio artifact beyond screenshots).
- Note what breaks first: latency degradation? memory pressure? errors?

### Day 19–20: Comparison report
- Write a short technical report (this becomes a blog post / portfolio doc):
  - Model comparison table: latency, tokens/sec, memory footprint.
  - What happened under load.
  - Self-hosted vs. API cost reasoning (rough compute-time-based estimate vs. what OpenAI/Anthropic API pricing would cost for equivalent volume).
  - Architecture diagram of the whole stack.

### Day 21: Wrap-up
- Clean up the repo, write a solid README (architecture diagram, setup instructions, screenshots of dashboards).
- Push to GitHub — this is the actual resume artifact.

---

## Stretch goals (only if Week 1–3 goes smoothly)
- Swap Filebeat-direct for Logstash if you want an enrichment step (e.g., tagging requests by cost tier).
- Add OpenTelemetry tracing → Elastic APM for full request tracing across the wrapper → Ollama call.
- Deploy on a local k8s cluster (kind/minikube) with Helm charts instead of docker-compose — strong "v2" story.
- Add a third model and a simple quality eval (not just speed) using a small labeled prompt set.

---

## Quick reference: what you need installed before Day 1
- Docker + Docker Compose
- Ollama (https://ollama.com)
- Python 3.10+ (for FastAPI wrapper)
- k6 or Locust (for load testing)
- A GitHub repo to commit to as you go (commit daily — it doubles as a build log for your write-up later)
