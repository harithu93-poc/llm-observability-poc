# Self-Hosted LLM Serving Platform — Comparison Report

**Author:** Hari
**Project:** Ollama-served LLMs with ELK observability, running on Windows 11 / WSL2
**Stack:** FastAPI · Ollama · Elasticsearch · Logstash · Kibana · Docker Compose

---

## 1. What was built

A production-style serving layer for two locally-hosted LLMs, fully instrumented and monitored
the way a platform engineer would monitor any microservice:

- **Serving layer:** Ollama running natively (WSL2 host) behind a containerized FastAPI wrapper.
  Every request is timed and logged as structured JSON — latency, tokens generated, tokens/sec,
  status, errors.
- **Observability layer:** Logstash tails the app log and ships structured documents into
  Elasticsearch; Kibana dashboards visualize latency percentiles, throughput, request volume,
  and error rate per model.
- **Alerting:** Kibana alerting rule on error-rate threshold, verified via forced failure and
  execution history.
- **Load testing:** k6, ramping 3→6 concurrent users across both models, observed live against
  the dashboard.

Architecture:
```
 k6 load test ──▶ FastAPI wrapper (Docker) ──▶ Ollama (native, WSL2 host)
                        │
                        ▼
                  app.log (JSON lines)
                        │
                        ▼
                    Logstash ──▶ Elasticsearch ──▶ Kibana (dashboards + alerting)
```

Hardware: Dell Precision 5540, Intel i7-9850H (6-core), 64GB RAM, NVIDIA Quadro T1000 (4GB VRAM).

---

## 2. Models compared

| | Llama 3.2 | Phi-4 |
|---|---|---|
| Parameters | 3B | 14B |
| Maker | Meta | Microsoft |
| Positioning | Lightweight, on-device, multilingual dialogue | Reasoning-optimized, larger |

Deliberately size-mismatched (3B vs 14B) rather than a same-class comparison — this turned out
to matter, see Section 4.

---

## 3. Results

> **Run `scripts/get-stats.sh` and replace the table below with your actual aggregated numbers.**
> Values marked *(observed)* are real; values marked *(sample — replace)* are placeholders to
> keep this report structurally complete until the full aggregation is pulled.

| Metric | Llama 3.2 | Phi-4 |
|---|---|---|
| Requests served | *(sample — replace)* | *(sample — replace)* |
| p50 latency | *(sample — replace)* | *(sample — replace)* |
| p95 latency | *(sample — replace)* | **27,795 ms** *(observed)* |
| Avg tokens/sec | *(sample — replace)* | **3.4** *(observed)* |
| Error rate | *(sample — replace)* | *(sample — replace)* |

---

## 4. Key finding: hardware-constrained inference

The standout result isn't a clean "bigger model = slower" story — it's a **VRAM ceiling** story.
A single Phi-4 request measured **27.8 seconds at 3.4 tokens/sec** — dramatically slower than
Llama 3.2's response time for a comparable prompt. The GPU on this hardware (Quadro T1000, 4GB
VRAM) cannot fit Phi-4's 14B parameters, so Ollama falls back to CPU for some or all of the
model's layers. Llama 3.2 (3B) fits comfortably and stays GPU-accelerated.

This is a more realistic and more interesting finding than a clean benchmark would have been:
**most self-hosted LLM deployments are hardware-constrained**, and knowing how to detect and
report that — rather than just reporting raw speed numbers — is the actual observability skill
being demonstrated here. Two options this suggests for a real deployment: (1) pick models sized
to fit available VRAM, or (2) provision hardware sized to the model, with cost implications
either way.

---

## 5. Behavior under load

*(Fill in after reviewing the Kibana dashboard for the k6 test window.)*

- What happened to p95 latency as concurrency increased from 3 → 6 users?
- Did error rate increase, or did requests just queue/slow down?
- Did Phi-4 requests visibly back up behind each other given their ~28s duration?

---

## 6. Self-hosted vs. API cost — rough reasoning

Self-hosting has no per-token billing; the real cost is **compute time** and **hardware
ownership**. As a rough proxy: total `latency_ms` summed per model approximates compute time
consumed. For comparison, hosted API pricing (e.g. OpenAI/Anthropic per-token rates) would be
billed per request regardless of local hardware constraints — meaning on constrained hardware
like this Quadro T1000, a hosted API would likely be **faster and cheaper per request** for a
model the size of Phi-4, while self-hosting a smaller model like Llama 3.2 is more clearly
favorable (no per-token cost, acceptable local latency).

This is the practical tradeoff worth stating plainly: **self-hosting only wins when the model
fits comfortably in the hardware you have.**

---

## 7. What I'd do next

- **RAG integration** — add a `/rag-chat` endpoint (retrieval + context injection) using the
  same observability logging already in place.
- **OpenTelemetry tracing** → Elastic APM, for full request tracing across wrapper → Ollama.
- **Kubernetes deployment** (kind/minikube + Helm) in place of docker-compose, as a stronger
  platform-engineering story.
- **Model-size-matched comparison** — add `phi4-mini` (3.8B) alongside Llama 3.2 for a cleaner
  apples-to-apples benchmark, separate from the deliberate size-mismatch story above.

---

## 8. Repo

Full source, dashboards config, and CI pipeline: see project README.
