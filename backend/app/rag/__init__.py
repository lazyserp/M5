"""
RAG (Retrieval-Augmented Generation) Module.

Provides modular subpackages:
- legacy: Naive character splitter, memory vector search & prototype pipeline.
- parsers: Tree-sitter AST syntax parsers & structural chunkers.
- indexing: Embeddings, Qdrant vector database store & code dependency graph.
- pipelines: Production Graph-RAG orchestrator pipelines.
"""

from app.rag.parsers.ast_parser import ASTParser
from app.rag.parsers.ast_chunker import ASTChunker
from app.rag.indexing.embedder import LocalEmbedder
from app.rag.indexing.qdrant_indexer import QdrantStore
from app.rag.indexing.dependency_graph import CodeDependencyGraph

__all__ = [
    "ASTParser",
    "ASTChunker",
    "LocalEmbedder",
    "QdrantStore",
    "CodeDependencyGraph",
]
