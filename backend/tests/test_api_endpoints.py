import os
import sys
from unittest.mock import Mock

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.endpoints import chat
from app.core.config import Settings
from app.main import create_app
def _settings() -> Settings:
    return Settings.from_environment({})


def _client(monkeypatch) -> tuple[TestClient, Mock]:
    app = create_app(_settings())
    model = Mock()
    model.chat.return_value = "The answer is grounded in supplied context."
    embedder = Mock()
    embedder.get_embeddings.return_value = [[0.1, 0.2]]
    store = Mock()
    store.search.return_value = [
        {
            "score": 0.91,
            "chunk": {
                "content": "def example(): pass", "repository_id": "demo-service",
                "commit_sha": "a" * 40, "file_path": "example.py", "start_line": 1,
                "end_line": 1, "chunk_id": "chunk-123",
            },
        }
    ]
    monkeypatch.setattr(chat, "_services", lambda _request: (model, embedder, store))
    return TestClient(app), store


def test_health_check() -> None:
    client = TestClient(create_app(_settings()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "m5-api"}


def test_chat_endpoint_uses_mocked_service_boundaries(monkeypatch) -> None:
    client, _ = _client(monkeypatch)

    response = client.post(
        "/api/v1/chat",
        json={
            "query": "What does example do?",
            "repository_id": "demo-service",
            "commit_sha": "a" * 40,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "The answer is grounded in supplied context.",
        "citations": [
            {
                "repository_id": "demo-service",
                "commit_sha": "a" * 40,
                "file_path": "example.py",
                "start_line": 1,
                "end_line": 1,
                "chunk_id": "chunk-123",
                "retrieval_score": 0.91,
            }
        ],
        "grounded": True,
        "confidence": "high",
    }
    assert response.json()["grounded"] is True


def test_chat_refuses_when_no_evidence_exists(monkeypatch) -> None:
    client, store = _client(monkeypatch)
    store.search.return_value = []

    response = client.post(
        "/api/v1/chat",
        json={
            "query": "What does example do?",
            "repository_id": "demo-service",
            "commit_sha": "a" * 40,
        },
    )

    assert response.json()["grounded"] is False
    assert response.json()["citations"] == []
