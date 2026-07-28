import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

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
    def __init__(
        self, workspace_root: str, qdrant_host: str = "localhost", qdrant_port: int = 6333
    ):
        self.workspace_root = os.path.abspath(workspace_root)
        self.embedder = LocalEmbedder()
        self.store = QdrantStore(host=qdrant_host, port=qdrant_port)
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

    def index_workspace(
        self,
        repository_id: str = "local-workspace",
        repository_url: str = "",
        branch: str = "",
        commit_sha: str = "",
        batch_size: int = 50,
        reset: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes two-pass indexing:
        Pass 1: Builds the global CodeDependencyGraph for all files.
        Pass 2: Parses AST blocks / character chunks, embeds in batches, and bulk upserts to Qdrant.
        """
        files = self.crawl_workspace()
        return self._index_files(
            files, repository_id, repository_url, branch, commit_sha, batch_size, reset
        )

    def index_changed_files(
        self,
        changed_files: Iterable[str],
        repository_id: str,
        repository_url: str,
        branch: str,
        commit_sha: str,
        deleted_files: Iterable[str] = (),
        batch_size: int = 50,
    ) -> Dict[str, Any]:
        files = []
        for relative_path in changed_files:
            path = (Path(self.workspace_root) / relative_path).resolve()
            if Path(self.workspace_root) not in path.parents or not path.is_file():
                continue
            files.append(str(path))
        for relative_path in deleted_files:
            path = (Path(self.workspace_root) / relative_path).resolve()
            if Path(self.workspace_root) not in path.parents:
                continue
            safe_path = os.path.relpath(path, self.workspace_root).replace("\\", "/")
            self.store.delete_file_chunks(repository_id, safe_path)
        return self._index_files(
            files, repository_id, repository_url, branch, commit_sha, batch_size, True
        )

    def _index_files(
        self,
        files: List[str],
        repository_id: str,
        repository_url: str,
        branch: str,
        commit_sha: str,
        batch_size: int,
        replace_existing: bool,
    ) -> Dict[str, Any]:
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
            relative_path = os.path.relpath(file_path, self.workspace_root).replace("\\", "/")
            if replace_existing:
                self.store.delete_file_chunks(repository_id, relative_path)
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
                    b["file"] = relative_path
                file_chunks = self.chunker.chunk_blocks(blocks)
            else:
                raw_chunks = chunk_file(file_path)
                file_chunks = [{"content": c["text"], "file": relative_path} for c in raw_chunks]

            for chunk in file_chunks:
                chunk.update(
                    {
                        "repository_id": repository_id,
                        "repository_url": repository_url,
                        "branch": branch,
                        "commit_sha": commit_sha,
                        "file_path": relative_path,
                    }
                )
                
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
