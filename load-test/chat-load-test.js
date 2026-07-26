import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 3 },   // ramp up to 3 concurrent users
    { duration: '1m', target: 3 },    // hold steady
    { duration: '30s', target: 6 },   // push harder
    { duration: '1m', target: 6 },    // hold
    { duration: '30s', target: 0 },   // ramp down
  ],
};

const prompts = [
  "Explain observability in one sentence.",
  "What is the capital of France?",
  "Summarize the concept of a load test.",
  "Give me a fun fact about the ocean.",
  "What does p95 latency mean?",
];

// NOTE: phi4 is slow on VRAM-constrained hardware (~28s/request observed).
// Weight requests toward llama3.2 so the test doesn't spend all its time
// queued on phi4 alone. Adjust this split once you have baseline numbers.
export default function () {
  const model = Math.random() < 0.7 ? 'llama3.2' : 'phi4';
  const prompt = prompts[Math.floor(Math.random() * prompts.length)];

  const res = http.post(
    'http://localhost:8000/chat',
    JSON.stringify({ prompt, model }),
    { headers: { 'Content-Type': 'application/json' }, timeout: '60s' }
  );

  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(1);
}