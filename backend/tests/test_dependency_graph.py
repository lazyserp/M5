import os
import sys

# Append backend/ directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag.dependency_graph import CodeDependencyGraph

def test_dependency_graph():
    # Target our RAG orchestrator file which imports multiple components
    target_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/rag/rag_pipeline.py'))
    
    print(f"[+] Scanning dependency graph for: {target_file}")
    
    # 1. Initialize the graph
    graph = CodeDependencyGraph()
    
    # 2. Add our target file to parse its imports
    graph.add_file(target_file)
    
    # 3. Retrieve its dependencies
    deps = graph.get_dependencies(target_file)
    
    print(f"[SUCCESS] Found {len(deps)} dependencies for {os.path.basename(target_file)}:\n")
    
    for idx, dep in enumerate(deps):
        print(f" Dependency {idx + 1}: {dep}")
        print(f"   Name: {os.path.basename(dep)}")
        print("-" * 50)

if __name__ == "__main__":
    test_dependency_graph()
