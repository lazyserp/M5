"""Local persistence for developer-demo identities, access grants, and audit records."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_ROLES = {"admin", "repository_manager", "developer", "auditor"}


class SecurityStore:
    """SQLite-backed store. Replace with PostgreSQL before a paid pilot."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL, role TEXT NOT NULL, active INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS repository_access (
                    user_id TEXT NOT NULL, repository_id TEXT NOT NULL,
                    PRIMARY KEY (user_id, repository_id)
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY, occurred_at TEXT NOT NULL, actor_id TEXT,
                    action TEXT NOT NULL, repository_id TEXT, commit_sha TEXT,
                    outcome TEXT NOT NULL, correlation_id TEXT NOT NULL, details TEXT NOT NULL
                );
                """
            )

    def create_user(self, username: str, password_hash: str, role: str) -> dict[str, str]:
        if role not in VALID_ROLES:
            raise ValueError("Unknown M5 role.")
        user = {"id": str(uuid.uuid4()), "username": username, "role": role}
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO users (id, username, password_hash, role, active) VALUES (?, ?, ?, ?, 1)",
                (user["id"], username, password_hash, role),
            )
        return user

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def grant_repository_access(self, user_id: str, repository_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO repository_access (user_id, repository_id) VALUES (?, ?)",
                (user_id, repository_id),
            )

    def can_access_repository(self, user: dict[str, Any], repository_id: str) -> bool:
        if user["role"] in {"admin", "repository_manager"}:
            return True
        with self._connect() as connection:
            return connection.execute(
                "SELECT 1 FROM repository_access WHERE user_id = ? AND repository_id = ?",
                (user["id"], repository_id),
            ).fetchone() is not None

    def record_audit(
        self, actor_id: str | None, action: str, outcome: str, correlation_id: str,
        repository_id: str | None = None, commit_sha: str | None = None, details: str = "{}",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(), actor_id, action,
                    repository_id, commit_sha, outcome, correlation_id, details,
                ),
            )

    def list_audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY occurred_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
