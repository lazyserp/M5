import uuid
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class QdrantStore:
    """
    Qdrant HNSW vector database storage and query manager.
    """
    def __init__(self, host: str = None, port: int = None):
        import os
        env_host = os.getenv("QDRANT_HOST")
        if env_host and env_host != "localhost":
            host = host or env_host
            port = port or int(os.getenv("QDRANT_PORT", "6333"))
        else:
            host = host or "localhost"
            port = port or int(os.getenv("QDRANT_PORT", "16333"))

        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "codebase_vectors"

    def init_collection(self, vector_size: int = 384):
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )

    def reset_collection(self, vector_size: int = 384):
        """Wipes all existing vectors and recreates a fresh collection for a new codebase."""
        if self.client.collection_exists(self.collection_name):
            self.client.delete_collection(self.collection_name)
        self.init_collection(vector_size=vector_size)

    def upload_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        points = []
        for chunk, vector in zip(chunks, embeddings):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["content"] + chunk.get("file", "")))
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "content": chunk["content"],
                    "type": chunk.get("type", "chunk"),
                    "name": chunk.get("name", "unknown"),
                    "start_line": chunk.get("start_line", 1),
                    "end_line": chunk.get("end_line", 1),
                    "file": chunk.get("file", "")
                }
            )
            points.append(point)

        self.client.upsert(collection_name=self.collection_name, points=points)
        
    def search(self, query_vector: List[float], top_k: int = 2) -> List[Dict[str, Any]]:
        search_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k
        )

        results = []
        for hit in search_result.points:
            results.append({
                "score": hit.score,
                "chunk": hit.payload
            })
        return results
