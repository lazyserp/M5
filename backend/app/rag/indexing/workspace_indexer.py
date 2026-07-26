import os
import sys
from typing import Any, Dict, List

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if backend_root not in sys.path:
    sys.path.append(backend_root)

from app.rag import (
    ASTChunker,
    ASTParser,
    CodeDependencyGraph,
    LocalEmbedder,
    QdrantStore,
)
from app.rag.legacy.simple_splitter import chunk_file

# Directories to skip
DEFAULT_IGNORE_DIRS = {
    ".git", ".vscode", ".idea", "node_modules", "venv", "env",
    "__pycache__", "dist", "build", "target", "out", "bin", "obj", ".mvn"
}

# Valid source file extensions
VALID_EXTENSIONS = {
    ".py", ".java", ".js", ".ts", ".cpp", ".h", ".c", ".cs",
    ".go", ".rs", ".md", ".sql", ".json", ".yaml", ".yml", ".xml", ".properties"
}

class WorkspaceIndexer:
    """
    Day 0 Enterprise Repository Batch Ingestion & Vector Indexing Engine.
    """
    def __init__(self, workspace_root: str):
        if "QDRANT_PORT" not in os.environ:
            os.environ["QDRANT_PORT"] = "16333"

        self.workspace_root = os.path.abspath(workspace_root)
        self.embedder = LocalEmbedder()
        self.store = QdrantStore()
        self.chunker = ASTChunker()
        self.graph = CodeDependencyGraph()
        
        # Ensure collection is initialized
        self.store.init_collection(vector_size=384)

    def crawl_workspace(self) -> List[str]:
        """
        Traverses the workspace directory tree and returns a list of valid source code files.
        """
        valid_files = []
        for root, dirs, files in os.walk(self.workspace_root):
            # Exclude ignored directories in-place
            dirs[:] = [d for d in dirs if d.lower() not in DEFAULT_IGNORE_DIRS]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in VALID_EXTENSIONS:
                    file_path = os.path.abspath(os.path.join(root, file))
                    valid_files.append(file_path)
        return valid_files

    def index_workspace(self, batch_size: int = 50, reset: bool = False) -> Dict[str, Any]:
        """
        Executes two-pass indexing:
        Pass 1: Builds the global CodeDependencyGraph for all files.
        Pass 2: Parses AST blocks / character chunks, embeds in batches, and bulk upserts to Qdrant.
        """
        if reset:
            print("[+] Resetting Qdrant collection for fresh codebase onboarding...")
            self.store.reset_collection(vector_size=384)

        files = self.crawl_workspace()
        print(f"[+] Discovered {len(files)} valid source files in: {self.workspace_root}")
        
        # Pass 1: Build global dependency graph
        print("[+] Pass 1/2: Building Global Code Dependency Graph...")
        for file_path in files:
            self.graph.add_file(file_path)
            
        # Pass 2: Ingest AST chunks into Qdrant
        print("[+] Pass 2/2: Ingesting code chunks into Qdrant...")
        total_chunks = 0
        all_chunks = []
        
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    code_content = f.read()
            except Exception:
                continue
                
            ext = file_path.split(".")[-1].lower()
            ext_map = {"py": "python", "java": "java", "js": "javascript", "ts": "typescript", "cpp": "cpp", "h": "cpp"}
            lang = ext_map.get(ext, "python")
            
            blocks = []
            try:
                p = ASTParser(language_name=lang)
                blocks = p.parse_code(code_content)
            except Exception:
                blocks = []
                
            if blocks:
                for b in blocks:
                    b["file"] = file_path
                file_chunks = self.chunker.chunk_blocks(blocks)
            else:
                raw_chunks = chunk_file(file_path)
                file_chunks = [{"content": c["text"], "file": file_path} for c in raw_chunks]
                
            all_chunks.extend(file_chunks)
            
            # When batch size is reached, generate embeddings and bulk upload to Qdrant
            if len(all_chunks) >= batch_size:
                texts = [c["content"] for c in all_chunks if c.get("content")]
                if texts:
                    embeddings = self.embedder.get_embeddings(texts)
                    self.store.upload_chunks(all_chunks, embeddings)
                    total_chunks += len(all_chunks)
                all_chunks = []
                
        # Upload remaining chunks
        if all_chunks:
            texts = [c["content"] for c in all_chunks if c.get("content")]
            if texts:
                embeddings = self.embedder.get_embeddings(texts)
                self.store.upload_chunks(all_chunks, embeddings)
                total_chunks += len(all_chunks)
                
        print(f"\n[SUCCESS] Pre-indexed {len(files)} files ({total_chunks} chunks) into Qdrant!")
        return {
            "status": "completed",
            "workspace_root": self.workspace_root,
            "total_files": len(files),
            "total_chunks": total_chunks
        }


def ensure_workspace_indexed(target_dir: str = "/app") -> dict:
    """
    Checks if vectors already exist in Qdrant.
    If 0 vectors exist (first run), automatically index workspace.
    If vectors exist (subsequent runs), log count and skip ingestion for 1-second startup.
    """
    store = QdrantStore()
    try:
        if store.client.collection_exists(store.collection_name):
            collection_info = store.client.get_collection(store.collection_name)
            points_count = collection_info.points_count
            if points_count and points_count > 0:
                print(f"[+] Codebase vectors already indexed (Found {points_count} vectors in Qdrant). Skipping startup ingestion!")
                return {"status": "skipped", "points_count": points_count}
    except Exception as e:
        print(f"[!] Warning checking collection status: {e}")

    print(f"[+] First-time container startup detected (0 vectors found). Automatically indexing workspace: {target_dir}...")
    indexer = WorkspaceIndexer(target_dir)
    return indexer.index_workspace(reset=False)

if __name__ == "__main__":
    target = "."
    should_reset = "--reset" in sys.argv or "-r" in sys.argv
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            target = arg
            break
            
    indexer = WorkspaceIndexer(target)
    indexer.index_workspace(reset=should_reset)
