"""M5 API application factory."""

from contextlib import asynccontextmanager
from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.webhooks import router as webhooks_router
from app.core.config import Settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-index workspace on container startup
    try:
        target_path = app.state.settings.workspace_root
        if target_path.is_dir():
            print(f"[+] Startup: Auto-indexing workspace at {target_path}...")
            from app.rag.indexing.workspace_indexer import WorkspaceIndexer
            indexer = WorkspaceIndexer(
                str(target_path),
                qdrant_host=app.state.settings.qdrant_host,
                qdrant_port=app.state.settings.qdrant_port,
            )
            indexer.index_workspace(reset=False)
    except Exception as err:
        print(f"[!] Startup auto-indexing skipped/failed: {err}")
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API in zero-auth developer mode."""
    app = FastAPI(
        title="M5 API",
        description="Intelligent Context Engine .",
        version="0.1.0",
        lifespan=lifespan,
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
    app.include_router(webhooks_router, prefix="/api/v1")

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "m5-api"}

    return app


app = create_app()
