import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# pyrefly: ignore [missing-import]
from app.rag.indexing.dependency_graph import CodeDependencyGraph

def test_dependency_graph():
    # Target our RAG orchestrator file which imports multiple components
    target_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/rag/pipelines/graph_rag_pipeline.py'))
    
    print(f"[+] Scanning dependency graph for: {target_file}")
    
    graph = CodeDependencyGraph()
    graph.add_file(target_file)
    deps = graph.get_dependencies(target_file)
    
    print(f"[SUCCESS] Found {len(deps)} dependencies for {os.path.basename(target_file)}:\n")
    
    for idx, dep in enumerate(deps):
        print(f" Dependency {idx + 1}: {dep}")
        print(f"   Name: {os.path.basename(dep)}")
        print("-" * 50)

if __name__ == "__main__":
    test_dependency_graph()
