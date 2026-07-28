"""Signed webhook endpoint for incremental repository indexing."""

from __future__ import annotations

import hashlib
import hmac
from typing import Callable

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.rag.indexing.workspace_indexer import WorkspaceIndexer

router = APIRouter()
MAX_WEBHOOK_BYTES = 1_000_000


class PushWebhook(BaseModel):
    """Provider-neutral push event produced by a trusted integration adapter."""

    repository_id: str = Field(min_length=1, max_length=128)
    repository_url: str = Field(min_length=1, max_length=2048)
    branch: str = Field(min_length=1, max_length=255)
    commit_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    changed_files: list[str] = Field(min_length=1, max_length=500)
    deleted_files: list[str] = Field(default_factory=list, max_length=500)


def _indexer(request: Request) -> WorkspaceIndexer:
    settings = request.app.state.settings
    return WorkspaceIndexer(
        str(settings.workspace_root), settings.qdrant_host, settings.qdrant_port
    )


def _valid_signature(body: bytes, supplied: str | None, secret: str) -> bool:
    if not supplied or not supplied.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied.removeprefix("sha256="), expected)


@router.post("/webhooks/push", status_code=status.HTTP_202_ACCEPTED)
async def receive_push_webhook(request: Request) -> dict[str, int | str]:
    """Verify and process changed files from an approved repository integration."""
    settings = request.app.state.settings
    if not settings.webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook integration is not configured.")

    body = await request.body()
    if len(body) > MAX_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="Webhook request is too large.")
    if not _valid_signature(body, request.headers.get("X-M5-Signature"), settings.webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    try:
        event = PushWebhook.model_validate_json(body)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Webhook payload is invalid.") from error

    result = _indexer(request).index_changed_files(
        event.changed_files,
        event.repository_id,
        event.repository_url,
        event.branch,
        event.commit_sha,
        event.deleted_files,
    )
    return {"status": "accepted", "indexed_files": result["total_files"]}
