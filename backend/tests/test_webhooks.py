import hashlib
import hmac
import json
import os
import sys
from unittest.mock import Mock

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.endpoints import webhooks
from app.core.config import Settings
from app.main import create_app


def _signed_headers(payload: bytes, secret: str) -> dict[str, str]:
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return {"X-M5-Signature": f"sha256={signature}"}


def test_signed_webhook_indexes_only_reported_files(monkeypatch) -> None:
    secret = "test-webhook-secret"
    payload = json.dumps(
        {
            "repository_id": "payments-service",
            "repository_url": "https://git.example.internal/payments-service",
            "branch": "main",
            "commit_sha": "a" * 40,
            "changed_files": ["src/payment.py"],
        }
    ).encode("utf-8")
    indexer = Mock()
    indexer.index_changed_files.return_value = {"total_files": 1}
    monkeypatch.setattr(webhooks, "_indexer", lambda _request: indexer)
    client = TestClient(create_app(Settings.from_environment({"M5_WEBHOOK_SECRET": secret})))

    response = client.post("/api/v1/webhooks/push", content=payload, headers=_signed_headers(payload, secret))

    assert response.status_code == 202
    assert response.json() == {"status": "accepted", "indexed_files": 1}
    indexer.index_changed_files.assert_called_once()


def test_webhook_rejects_an_invalid_signature() -> None:
    payload = b'{"repository_id":"payments-service"}'
    client = TestClient(create_app(Settings.from_environment({"M5_WEBHOOK_SECRET": "secret"})))

    response = client.post(
        "/api/v1/webhooks/push", content=payload, headers={"X-M5-Signature": "sha256=bad"}
    )

    assert response.status_code == 401
