import os
import sys

#  Append parent directory so Python can find 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

target_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/core/llm_client.py'))

from app.rag.ast_parser import ASTParser
from app.rag.ast_chunker import ASTChunker
from app.rag.embedder import LocalEmbedder
from app.rag.qdrant_indexer import QdrantStore

def test_qdrant():
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

        parser = ASTParser()
        code_blocks = parser.parse_code(content)
        
        # Tag each block with target_file so ASTChunker knows file type
        for block in code_blocks:
            block["file"] = target_file

        chunker = ASTChunker()
        chunked_code = chunker.chunk_blocks(code_blocks)

        embedder = LocalEmbedder()
        texts = [code["content"] for code in chunked_code]
        vectors = embedder.get_embeddings(texts)

        store = QdrantStore()
        store.init_collection(vector_size=384)

        # 2. Upload chunks to Qdrant before searching!
        print("[+] Uploading chunks and vectors to Qdrant...")
        store.upload_chunks(chunked_code, vectors)

        query_string = embedder.get_embeddings(["How does the chat function work?"])[0]

        print("[+] Querying Qdrant database...")
        results = store.search(query_string)

        for item in results:
            print(f"\n score : {item['score']} \n chunk: {item['chunk']}")

if __name__ == "__main__":
    test_qdrant()
