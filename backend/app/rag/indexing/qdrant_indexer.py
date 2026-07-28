import uuid
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from app.rag.indexing.identity import chunk_id


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

    def reset_collection(self, vector_size: int = 384):
        """Wipes all existing vectors and recreates a fresh collection for a new codebase."""
        if self.client.collection_exists(self.collection_name):
            self.client.delete_collection(self.collection_name)
        self.init_collection(vector_size=vector_size)

    def upload_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        points = []
        for chunk, vector in zip(chunks, embeddings):
            stable_id = chunk.get("chunk_id") or chunk_id(chunk)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, stable_id))
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "content": chunk["content"],
                    "type": chunk.get("type", "chunk"),
                    "name": chunk.get("name", "unknown"),
                    "start_line": chunk.get("start_line", 1),
                    "end_line": chunk.get("end_line", 1),
                    "file": chunk.get("file_path", chunk.get("file", "")),
                    "file_path": chunk.get("file_path", chunk.get("file", "")),
                    "chunk_id": stable_id,
                    "repository_id": chunk.get("repository_id", "local-workspace"),
                    "repository_url": chunk.get("repository_url", ""),
                    "branch": chunk.get("branch", ""),
                    "commit_sha": chunk.get("commit_sha", ""),
                }
            )
            points.append(point)

        self.client.upsert(collection_name=self.collection_name, points=points)

    def delete_file_chunks(self, repository_id: str, file_path: str) -> None:
        """Remove older chunks for one repository file before re-indexing it."""
        selector = Filter(
            must=[
                FieldCondition(key="repository_id", match=MatchValue(value=repository_id)),
                FieldCondition(key="file_path", match=MatchValue(value=file_path)),
            ]
        )
        self.client.delete(collection_name=self.collection_name, points_selector=selector)
        
    def search(
        self,
        query_vector: List[float],
        repository_id: str | None = None,
        commit_sha: str | None = None,
        top_k: int = 2,
    ) -> List[Dict[str, Any]]:
        filters = []
        if repository_id:
            filters.append(
                FieldCondition(key="repository_id", match=MatchValue(value=repository_id))
            )
        if commit_sha:
            filters.append(FieldCondition(key="commit_sha", match=MatchValue(value=commit_sha)))
        search_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k
            ,query_filter=Filter(must=filters) if filters else None
        )

        results = []
        for hit in search_result.points:
            results.append({
                "score": hit.score,
                "chunk": hit.payload
            })
        return results
