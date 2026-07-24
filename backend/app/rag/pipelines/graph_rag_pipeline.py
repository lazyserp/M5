import os
import sys
from typing import List, Dict, Any
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Append parent directory tree so Python can find 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.core.llm_client import LocalLLMClient
from app.rag.parsers.ast_parser import ASTParser
from app.rag.parsers.ast_chunker import ASTChunker
from app.rag.indexing.embedder import LocalEmbedder
from app.rag.indexing.qdrant_indexer import QdrantStore
from app.rag.indexing.dependency_graph import CodeDependencyGraph


def run_graph_rag(target_file: str, query: str):
    target_file = os.path.abspath(target_file)

    client = LocalLLMClient()
    embedder = LocalEmbedder()
    store = QdrantStore()
    parser = ASTParser()
    chunker = ASTChunker()
    graph = CodeDependencyGraph()

    store.init_collection(vector_size=384)

    graph.add_file(target_file)
    dependencies = graph.get_dependencies(target_file)
    files_to_index = [target_file] + dependencies

    print("\n[+] Ingesting codebases into Qdrant...")
    for file_path in files_to_index:
        if not os.path.exists(file_path):
            continue
        with open(file_path, 'r', encoding="utf-8") as f:
            code_content = f.read()

        blocks = parser.parse_code(code_content)

        for b in blocks:
            b["file"] = file_path

        chunks = chunker.chunk_blocks(blocks)
        texts = [c["content"] for c in chunks]
        embeddings = embedder.get_embeddings(texts)

        # Upload chunks to the local Qdrant container
        store.upload_chunks(chunks, embeddings)

    print("\n[+] Performing Semantic Vector Search...")
    query_vector = embedder.get_embeddings([query])[0]
    primary_matches = store.search(query_vector, top_k=2)

    retrieved_chunks = []
    referenced_files = set()

    for match in primary_matches:
        chunk = match["chunk"]
        retrieved_chunks.append(chunk)
        referenced_files.add(chunk["file"])

    print("\n[+] Walking Dependency Graph (Graph RAG Expansion)...")
    expanded_chunks = []
    for file_path in referenced_files:
        deps = graph.get_dependencies(file_path)
        for dep in deps:
            print(f"    Graph-RAG: Fetching context from dependency: {os.path.basename(dep)}") 
            
            # Query Qdrant using metadata filters to retrieve chunks belonging to 'dep'
            dep_points, _ = store.client.scroll(
                collection_name=store.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="file",
                            match=MatchValue(value=dep)
                        )
                    ]
                ),
                limit=2
            )
            for point in dep_points:
                expanded_chunks.append(point.payload)

    # Merge results (avoiding duplicates)
    final_context_chunks = []
    seen_contents = set()
    
    for c in retrieved_chunks + expanded_chunks:
        if c["content"] not in seen_contents:
            final_context_chunks.append(c)
            seen_contents.add(c["content"])
            
    # Format the context block
    context = "\n---\n".join([c["content"] for c in final_context_chunks])
    
    system_prompt = (
        "You are an on-premise enterprise code assistant. Answer the user's question using ONLY the provided code context. "
        "If the answer cannot be derived from the context, say 'I do not know'.\n\n"
        f"CONTEXT:\n{context}"
    )
    
    print("\n[+] Querying Local LLM...")
    answer = client.chat(system_prompt, query)
    print(f"\n[ANSWER FROM GRAPH-RAG]:\n{answer}\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python graph_rag_pipeline.py <file_path> <query>")
    else:
        run_graph_rag(sys.argv[1], sys.argv[2])
