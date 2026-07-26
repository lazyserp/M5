import os
import sys

# Default QDRANT_PORT to 16333 if not specified
if "QDRANT_PORT" not in os.environ:
    os.environ["QDRANT_PORT"] = "16333"

# Append backend directory so Python can find 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag.indexing.workspace_indexer import WorkspaceIndexer


def test_workspace_indexer():
    # Target our backend codebase directory to index
    target_workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app'))
    
    print(f"\n[+] Testing Day 0 Workspace Indexer over: {target_workspace}")
    
    indexer = WorkspaceIndexer(target_workspace)
    result = indexer.index_workspace(batch_size=10)
    
    print(f"    Status: {result.get('status')}")
    print(f"    Total Files Crawled: {result.get('total_files')}")
    print(f"    Total Chunks Vectorized & Upserted: {result.get('total_chunks')}")
    
    assert result.get("status") == "completed"
    assert result.get("total_files") > 0
    assert result.get("total_chunks") > 0
    print("\n[SUCCESS] Day 0 Workspace Indexer test completed successfully!")

if __name__ == "__main__":
    test_workspace_indexer()
