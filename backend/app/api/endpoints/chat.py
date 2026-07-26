import os
import sys

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


class ChatRequest(BaseModel):
    query: str
    file_path: str | None = None


class ChatResponse(BaseModel):
    answer: str
    target_file: str | None = None


class IndexRequest(BaseModel):
    workspace_path: str | None = None
    reset: bool = True


class IndexResponse(BaseModel):
    status: str
    workspace_root: str
    total_files: int
    total_chunks: int


# Import modules from top-level app.rag package initializer
from app.core.llm_client import LocalLLMClient
from app.rag import (
    ASTChunker,
    ASTParser,
    CodeDependencyGraph,
    LocalEmbedder,
    QdrantStore,
)
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.rag.legacy.simple_splitter import chunk_file


def get_language_from_extension(file_path: str) -> str:
    ext = file_path.split(".")[-1].lower()
    ext_map = {
        "py": "python",
        "java": "java",
        "js": "javascript",
        "ts": "typescript",
        "cpp": "cpp",
        "h": "cpp",
        "c": "cpp",
    }
    return ext_map.get(ext, "python")


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    client = LocalLLMClient()
    embedder = LocalEmbedder()
    store = QdrantStore()

    store.init_collection(vector_size=384)
    query_vector = embedder.get_embeddings([request.query])[0]
    primary_matches = store.search(query_vector, top_k=5)

    retrieved_chunks = [match["chunk"] for match in primary_matches if match.get("chunk")]

    if not retrieved_chunks:
        return ChatResponse(answer="I do not have enough code context indexed in Qdrant to answer this question.", target_file=request.file_path)

    context = "\n---\n".join([c.get("content", c.get("text", "")) for c in retrieved_chunks])
    system_prompt = (
        "You are an expert on-premise enterprise AI code assistant. "
        "Analyze the provided code and documentation context carefully to answer the user's question accurately, clearly, and concisely.\n\n"
        f"CONTEXT:\n{context}"
    )

    answer = client.chat(system_prompt, request.query)
    return ChatResponse(answer=answer, target_file=request.file_path)


@router.post("/chat/stream")
def chat_stream_endpoint(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    client = LocalLLMClient()
    embedder = LocalEmbedder()
    store = QdrantStore()

    store.init_collection(vector_size=384)
    query_vector = embedder.get_embeddings([request.query])[0]
    primary_matches = store.search(query_vector, top_k=5)

    retrieved_chunks = [match["chunk"] for match in primary_matches if match.get("chunk")]

    if not retrieved_chunks:
        def empty_generator():
            yield "I do not have enough code context indexed in Qdrant to answer this question."
        return StreamingResponse(empty_generator(), media_type="text/event-stream")

    context = "\n---\n".join([c.get("content", c.get("text", "")) for c in retrieved_chunks])
    system_prompt = (
        "You are an expert on-premise enterprise AI code assistant. "
        "Analyze the provided code and documentation context carefully to answer the user's question accurately, clearly, and concisely.\n\n"
        f"CONTEXT:\n{context}"
    )

    def event_generator():
        try:
            for chunk in client.chat_stream(system_prompt, request.query):
                yield f"{chunk}"
        except Exception as e:
            yield f"\n[Streaming Error: {str(e)}]"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/index")
def index_workspace_endpoint(request: IndexRequest):
    from app.rag.indexing.workspace_indexer import WorkspaceIndexer
    target_path = request.workspace_path or os.getenv("WORKSPACE_ROOT", "/app")
    if not os.path.exists(target_path):
        target_path = "/app"

    indexer = WorkspaceIndexer(target_path)
    result = indexer.index_workspace(reset=request.reset)
    return IndexResponse(**result)
