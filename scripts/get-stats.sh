#!/bin/bash
# Pulls aggregated latency/throughput/error stats per model from Elasticsearch.
# Run from anywhere with curl access to localhost:9200.

curl -s -X GET "http://localhost:9200/llm-observability-*/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 0,
    "aggs": {
      "by_model": {
        "terms": { "field": "model.keyword" },
        "aggs": {
          "total_requests": { "value_count": { "field": "model.keyword" } },
          "error_count": {
            "filter": { "term": { "status.keyword": "error" } }
          },
          "latency_percentiles": {
            "percentiles": { "field": "latency_ms", "percents": [50, 95] }
          },
          "avg_tokens_per_sec": {
            "avg": { "field": "tokens_per_second" }
          },
          "sum_latency_ms": {
            "sum": { "field": "latency_ms" }
          }
        }
      }
    }
  }'
