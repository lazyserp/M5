import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend root is on sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.api.endpoints.chat import router as chat_router

app = FastAPI(
    title="M5 - Air-Gapped AI Assistant API",
    description="Backend API serving Graph-RAG code context to VS Code",
    version="1.0.0"
)

# Configure CORS so VS Code webviews can talk to localhost HTTP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount endpoints under /api/v1
app.include_router(chat_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Project M5 Backend API"}


@app.on_event("startup")
def startup_event():
    import threading
    from app.rag.indexing.workspace_indexer import ensure_workspace_indexed
    target_workspace = os.getenv("WORKSPACE_ROOT", "/app")
    threading.Thread(target=ensure_workspace_indexed, args=(target_workspace,), daemon=True).start()
