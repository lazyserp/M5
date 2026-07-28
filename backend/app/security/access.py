"""Request authentication and repository authorization checks."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from app.security.auth import AuthenticationError, read_access_token


def authenticated_user(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    header = request.headers.get("Authorization", "")
    if not settings.auth_secret or not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication is required.")
    try:
        user_id = read_access_token(header.removeprefix("Bearer "), settings.auth_secret)
    except AuthenticationError as error:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.") from error
    user = request.app.state.security_store.get_user(user_id)
    if not user or not user["active"]:
        raise HTTPException(status_code=401, detail="User account is unavailable.")
    return user


def require_repository_access(request: Request, repository_id: str) -> dict[str, Any]:
    user = authenticated_user(request)
    if not request.app.state.security_store.can_access_repository(user, repository_id):
        request.app.state.security_store.record_audit(
            user["id"], "query", "denied", "authorization", repository_id=repository_id
        )
        raise HTTPException(status_code=403, detail="Repository access is denied.")
    return user


def require_role(request: Request, *roles: str) -> dict[str, Any]:
    user = authenticated_user(request)
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail="Role is not permitted for this action.")
    return user
