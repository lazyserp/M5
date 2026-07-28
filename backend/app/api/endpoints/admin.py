"""Small local administration API for M5 developer deployments."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.security.access import require_role
from app.security.auth import hash_password

router = APIRouter()
Role = Literal["admin", "repository_manager", "developer", "auditor"]


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=12, max_length=1024)
    role: Role


class GrantAccessRequest(BaseModel):
    username: str = Field(min_length=3, max_length=128)
    repository_id: str = Field(min_length=1, max_length=128)


@router.post("/admin/users", status_code=201)
def create_user(request: Request, payload: CreateUserRequest) -> dict[str, str]:
    actor = require_role(request, "admin")
    try:
        user = request.app.state.security_store.create_user(
            payload.username, hash_password(payload.password), payload.role
        )
    except Exception as error:
        raise HTTPException(status_code=409, detail="Username already exists.") from error
    request.app.state.security_store.record_audit(actor["id"], "create_user", "success", "admin")
    return user


@router.post("/admin/repository-access", status_code=204)
def grant_repository_access(request: Request, payload: GrantAccessRequest) -> None:
    actor = require_role(request, "admin", "repository_manager")
    user = request.app.state.security_store.get_user_by_username(payload.username)
    if not user:
        raise HTTPException(status_code=404, detail="User was not found.")
    request.app.state.security_store.grant_repository_access(user["id"], payload.repository_id)
    request.app.state.security_store.record_audit(
        actor["id"], "grant_repository_access", "success", "admin", payload.repository_id
    )


@router.get("/audit")
def read_audit_events(request: Request, limit: int = 100) -> list[dict[str, object]]:
    require_role(request, "admin", "auditor")
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 500.")
    return request.app.state.security_store.list_audit_events(limit)
