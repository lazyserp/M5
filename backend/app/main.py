"""M5 API application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.admin import router as admin_router
from app.api.endpoints.webhooks import router as webhooks_router
from app.core.config import Settings
from app.security.store import SecurityStore
from app.security.auth import hash_password


def _bootstrap_admin(app: FastAPI) -> None:
    """Create a one-time local admin only when explicitly configured."""
    settings = app.state.settings
    if not settings.bootstrap_admin_username or not settings.bootstrap_admin_password:
        return
    if app.state.security_store.get_user_by_username(settings.bootstrap_admin_username):
        return
    app.state.security_store.create_user(
        settings.bootstrap_admin_username,
        hash_password(settings.bootstrap_admin_password),
        "admin",
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API without accessing repositories or external services at startup."""
    app = FastAPI(
        title="M5 Code Intelligence API",
        description="Customer-controlled, evidence first code intelligence service.",
        version="0.1.0",
    )
    app.state.settings = settings or Settings.from_environment()
    app.state.security_store = SecurityStore(app.state.settings.database_path)
    _bootstrap_admin(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app.state.settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(webhooks_router, prefix="/api/v1")

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "m5-api"}

    return app


app = create_app()
