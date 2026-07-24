import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# pyrefly: ignore [missing-import]
from app.rag.legacy.simple_splitter import chunk_file

def test_splitter():
    target_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/core/llm_client.py'))
    print(f" Testing splitter on {target_file}")
    
    chunks = chunk_file(target_file, chunk_size=300, overlap=40)
    print(f"[SUCCESS] File split into {len(chunks)} chunks!")

    for chunk in chunks:
        print(f"\n--- CHUNK {chunk['id']} (Chars {chunk['start_char']} to {chunk['end_char']}) ---")
        print(chunk['text'])
        print("-" * 40)

if __name__ == "__main__":
    test_splitter()
