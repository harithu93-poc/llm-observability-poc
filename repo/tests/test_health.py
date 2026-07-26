"""
Basic smoke tests for the FastAPI wrapper.

Kept deliberately light for CI: /health doesn't touch Ollama, so this runs
green in GitHub Actions without needing a live model. /chat is exercised
manually / in integration testing where Ollama is actually running.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_rejects_unknown_model():
    response = client.post(
        "/chat",
        json={"prompt": "hello", "model": "not-a-real-model"},
    )
    assert response.status_code == 400
