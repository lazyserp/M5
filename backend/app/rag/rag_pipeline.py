import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.core.llm_client import LocalLLMClient
from app.rag.simple_splitter import chunk_file
from app.rag.embedder import LocalEmbedder
from app.rag.memory_search import MemoryVectorStore

def run_rag(file_path : str , query : str):
    client = LocalLLMClient()
    embedder = LocalEmbedder()
    store = MemoryVectorStore()

    print("--- Chunking File ---")
    chunks = chunk_file(file_path)

    texts = [c["text"] for c in chunks]


    print("--- Generating Embeddings ---")
    embeddings = embedder.get_embeddings(texts)

    store.add_chunks(chunks,embeddings)

    print(" --- Querying vector store... ---")
    query_vec = embedder.get_embeddings([query])[0]
    search_results = store.search(query_vec,top_k=2)    

    context = "\n---\n".join([r["chunk"]["text"] for r in search_results])

    system_prompt = (
        "You are an on-premise code assistant. Answer the user's question using ONLY the provided code context. "
        "If the answer cannot be derived from the context, say 'I do not know'.\n\n"
        f"CONTEXT:\n{context}"
    )


    print("[+] Sending payload to local LLM...")
    answer = client.chat(system_prompt, query)
    print(f"\n[ANSWER]:\n{answer}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python rag_pipeline.py <file_path> <query>")
    else:
        # Run the pipeline with the arguments passed in the terminal
        run_rag(sys.argv[1], sys.argv[2])




