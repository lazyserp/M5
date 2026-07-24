import numpy as np
from typing import List, Dict, Any

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Computes cosine similarity score between two dense vectors.
    """
    dot = np.dot(v1, v2)
    norm_a = np.linalg.norm(v1)
    norm_b = np.linalg.norm(v2)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    
    return float(dot / (norm_a * norm_b))


class MemoryVectorStore:
    """
    Phase 1 Naive In-Memory NumPy Vector Store.
    """
    def __init__(self):
        self.registry: List[Dict[str, Any]] = [] # Holds text chunks
        self.vectors: List[np.ndarray] = []     # Holds NumPy vector arrays

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        for chunk, vector in zip(chunks, embeddings):
            self.registry.append(chunk)
            self.vectors.append(np.array(vector))

    def search(self, query_vector: List[float], top_k: int = 2) -> List[Dict[str, Any]]:
        q_vec = np.array(query_vector)
        scores = [cosine_similarity(q_vec, v) for v in self.vectors]
        ranked_indices = np.argsort(scores)[::-1][:top_k]
        results = []

        for i in ranked_indices:
            result_dict = {"chunk": self.registry[i], "score": scores[i]}
            results.append(result_dict)

        return results
