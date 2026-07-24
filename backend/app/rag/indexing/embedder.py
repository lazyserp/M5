from sentence_transformers import SentenceTransformer
from typing import List

class LocalEmbedder:
    """
    Local SentenceTransformer embeddings model wrapper.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
