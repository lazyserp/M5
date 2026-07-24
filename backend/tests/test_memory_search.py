
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.rag.memory_search import MemoryVectorStore
from app.rag.simple_splitter import chunk_file
from app.rag.embedder import LocalEmbedder


def test_memory_search():
    target_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/core/llm_client.py'))
    content = chunk_file(target_file)

    embedder = LocalEmbedder()
    texts = [chunk["text"] for chunk in content]
    embeddings = embedder.get_embeddings(texts)

    memory_store = MemoryVectorStore()
    memory_store.add_chunks(content,embeddings)

    query_vector = embedder.get_embeddings(["How do we call the Ollama API?"])[0]
    result = memory_store.search(query_vector)


    print("\n--- SEARCH RESULTS ---")
    for item in result:
        print(f"Score: {item['score']:.4f}")
        print(f"Chunk Text:\n{item['chunk']['text']}")
        print("=" * 60)
        
if __name__ == "__main__":
    test_memory_search()








