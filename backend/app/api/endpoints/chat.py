import os
import sys
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

class ChatRequest(BaseModel):
    query : str
    file_path: str | None = None

class ChatResponse(BaseModel):
    answer: str
    target_file : str | None = None


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

router = APIRouter()

@router.post("/chat" , response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):  
    if not request.query.strip():
        raise HTTPException(status_code=400 , detail="Query string cannot be empty")

    file_path = request.file_path
    if not file_path or not os.path.exists(file_path):
        # Default fallback to a known pipeline file if none is passed
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../rag/rag_pipeline.py'))


    # Run Graph-RAG Retrieval
    client = LocalLLMClient()
    embedder = LocalEmbedder()
    store = QdrantStore()
    parser = ASTParser()
    chunker = ASTChunker()
    graph = CodeDependencyGraph()
    
    store.init_collection(vector_size=384)

    graph.add_file(file_path)
   
    dependencies = graph.get_dependencies(file_path)
    files_to_index = [file_path] + dependencies

    for f_path in files_to_index:
        if not os.path.exists(f_path):
            continue
        with open(f_path,'r',encoding="utf-8") as f:
            code_content = f.read()
        
        blocks = parser.parse_code(code_content)
        for b in blocks:
            b["file"] = f_path
        
        chunks = chunker.chunk_blocks(blocks)
        texts = [c["content"] for c in chunks]
        embeddings = embedder.get_embeddings(texts)
        store.upload_chunks(chunks, embeddings)

    query_vector = embedder.get_embeddings([request.query])[0]
    primary_matches = store.search(query_vector, top_k=2)

    retrieved_chunks = []
    referenced_files = set()

    for match in primary_matches:
        chunk = match["chunk"]
        retrieved_chunks.append(chunk)
        referenced_files.add(chunk["file"])

    expanded_chunks = []
    for f_p in referenced_files:
        deps = graph.get_dependencies(f_p)
        for dep in deps:
            dep_points, _ = store.client.scroll(
                collection_name=store.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="file", match=MatchValue(value=dep))]
                ),
                limit=2
            )
            for point in dep_points:
                expanded_chunks.append(point.payload)

    final_context_chunks = []
    seen_contents = set()
    for c in retrieved_chunks + expanded_chunks:
        if c["content"] not in seen_contents:
            final_context_chunks.append(c)
            seen_contents.add(c["content"])
            
    context = "\n---\n".join([c["content"] for c in final_context_chunks])
    system_prompt = (
        "You are an on-premise enterprise code assistant. Answer the user's question using ONLY the provided code context. "
        "If the answer cannot be derived from the context, say 'I do not know'.\n\n"
        f"CONTEXT:\n{context}"
    )
    
    answer = client.chat(system_prompt, request.query)
    return ChatResponse(answer=answer, target_file=file_path)