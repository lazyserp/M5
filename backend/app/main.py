"""M5 API application factory."""

from app.api.endpoints.chat import router as chat_router
from app.core.config import Settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API in zero-auth developer mode."""
    app = FastAPI(
        title="M5 API",
        description="Intelligent Context Engine .",
        version="0.1.0",
    )
    app.state.settings = settings or Settings.from_environment()
    allowed_origins = list(app.state.settings.allowed_origins) if app.state.settings.allowed_origins else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(chat_router, prefix="/api/v1")

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "m5-api"}

    return app


app = create_app()
