import os
import sys
from unittest.mock import Mock

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.endpoints import chat
from app.core.config import Settings
from app.main import create_app
from app.security.auth import hash_password


def _settings(tmp_path) -> Settings:
    return Settings.from_environment(
        {"M5_AUTH_SECRET": "test-secret", "M5_DATABASE_PATH": str(tmp_path / "m5-test.db")}
    )


def _authorized_client(tmp_path, monkeypatch) -> tuple[TestClient, dict[str, str], Mock]:
    app = create_app(_settings(tmp_path))
    user = app.state.security_store.create_user("developer", hash_password("correct-password"), "developer")
    app.state.security_store.grant_repository_access(user["id"], "demo-service")
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
    from app.security.auth import create_access_token
    token = create_access_token(user["id"], "test-secret", 60)
    return TestClient(app), {"Authorization": f"Bearer {token}"}, store


def test_health_check(tmp_path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "m5-api"}


def test_chat_endpoint_uses_mocked_service_boundaries(tmp_path, monkeypatch) -> None:
    client, headers, _ = _authorized_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/v1/chat",
        json={
            "query": "What does example do?",
            "repository_id": "demo-service",
            "commit_sha": "a" * 40,
        }, headers=headers,
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


def test_chat_refuses_when_no_evidence_exists(tmp_path, monkeypatch) -> None:
    client, headers, store = _authorized_client(tmp_path, monkeypatch)
    store.search.return_value = []

    response = client.post(
        "/api/v1/chat",
        json={
            "query": "What does example do?",
            "repository_id": "demo-service",
            "commit_sha": "a" * 40,
        }, headers=headers,
    )

    assert response.json()["grounded"] is False
    assert response.json()["citations"] == []
