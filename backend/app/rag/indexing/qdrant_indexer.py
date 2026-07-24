import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantStore:
    """
    Qdrant HNSW vector database storage and query manager.
    """
    def __init__(self, host: str = "localhost", port: int = 6333):
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

    def upload_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        points = []
        for chunk, vector in zip(chunks, embeddings):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["content"] + chunk.get("file", "")))
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "content": chunk["content"],
                    "type": chunk["type"],
                    "name": chunk["name"],
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
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
