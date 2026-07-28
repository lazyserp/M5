"""Local authentication endpoints for M5 developer deployments."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.security.auth import create_access_token, verify_password

router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=12, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/auth/login", response_model=TokenResponse)
def login(request: Request, payload: LoginRequest) -> TokenResponse:
    settings = request.app.state.settings
    if not settings.auth_secret:
        raise HTTPException(status_code=503, detail="Authentication is not configured.")
    user = request.app.state.security_store.get_user_by_username(payload.username)
    if not user or not user["active"] or not verify_password(payload.password, user["password_hash"]):
        request.app.state.security_store.record_audit(None, "login", "denied", "login")
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = create_access_token(user["id"], settings.auth_secret, settings.auth_token_minutes)
    request.app.state.security_store.record_audit(user["id"], "login", "success", "login")
    return TokenResponse(access_token=token)
