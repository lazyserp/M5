import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import Settings
from app.main import create_app
from app.security.auth import create_access_token, hash_password, verify_password


def _app(tmp_path):
    return create_app(
        Settings.from_environment(
            {"M5_AUTH_SECRET": "test-secret", "M5_DATABASE_PATH": str(tmp_path / "security.db")}
        )
    )


def test_password_hash_cannot_be_used_as_a_password() -> None:
    password_hash = hash_password("a-long-test-password")

    assert verify_password("a-long-test-password", password_hash)
    assert not verify_password(password_hash, password_hash)


def test_user_without_repository_access_is_denied(tmp_path) -> None:
    app = _app(tmp_path)
    user = app.state.security_store.create_user("unauthorised", hash_password("a-long-test-password"), "developer")
    token = create_access_token(user["id"], "test-secret", 60)
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Where is payment validation?", "repository_id": "protected", "commit_sha": "a" * 40},
    )

    assert response.status_code == 403
