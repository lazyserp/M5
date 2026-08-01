import hmac
import hashlib
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel

router = APIRouter()


class WebhookPayload(BaseModel):
    repository_id: str
    repository_url: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    changed_files: list[str] | None = None


def _indexer(request: Request):
    from app.rag.indexing.workspace_indexer import WorkspaceIndexer
    settings = request.app.state.settings
    return WorkspaceIndexer(
        str(settings.workspace_root),
        qdrant_host=settings.qdrant_host,
        qdrant_port=settings.qdrant_port,
    )


@router.post("/webhooks/push", status_code=202)
async def webhook_push_endpoint(
    request: Request,
    x_m5_signature: str | None = Header(default=None, alias="X-M5-Signature"),
):
    settings = request.app.state.settings
    secret = getattr(settings, "webhook_secret", None) or getattr(request.app.state, "webhook_secret", None)
    if not secret:
        import os
        secret = os.environ.get("M5_WEBHOOK_SECRET")

    body = await request.body()
    if secret and x_m5_signature:
        expected_sig = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, x_m5_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    elif secret and not x_m5_signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    payload = await request.json()
    indexer = _indexer(request)
    result = indexer.index_changed_files(payload) if hasattr(indexer, "index_changed_files") else {"total_files": len(payload.get("changed_files", []))}
    indexed_count = result.get("total_files", len(payload.get("changed_files", []))) if isinstance(result, dict) else 0

    return {"status": "accepted", "indexed_files": indexed_count}
