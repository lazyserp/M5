import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.rag.embedder import LocalEmbedder


def test_embeddings():
    embedder = LocalEmbedder()
    sentences = [
                    "How to connect to a database",
                    "Establishing database connections",
                    "How to bake a chocolate chip cookie"
                ]
    vectors = embedder.get_embeddings(sentences)

    print("Vectors REturned: ----------------")

    for i,vec in enumerate(vectors):
        print(f"Sentence: {sentences[i]} -> Vector Dimensions : { len(vec)}" )
        print(f"First five numebrs of the vector : {vec[:5]}")



if __name__ == "__main__":
    test_embeddings()

