import os
import sys

# Append backend root directory so Python can resolve the 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# pyrefly: ignore [missing-import]
from app.rag.pipelines.graph_rag_pipeline import run_graph_rag

def test_pipeline():
    """
    Integration test for Graph-RAG Pipeline.
    Prerequisites:
    1. Qdrant Docker container running on localhost:6333
    2. Ollama running on localhost:11434 with qwen2.5-coder:1.5b pulled
    """
    # Select a target file within the codebase to index and query
    sample_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../app/rag/pipelines/graph_rag_pipeline.py')
    )
    query = "How does Graph RAG retrieve context from imported dependency files?"

    print(f"[+] Testing Graph-RAG Pipeline on target file: {sample_file}")
    print(f"[+] Query: '{query}'\n")

    run_graph_rag(sample_file, query)

if __name__ == "__main__":
    test_pipeline()
