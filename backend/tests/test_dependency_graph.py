import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# pyrefly: ignore [missing-import]
from app.rag.indexing.dependency_graph import CodeDependencyGraph


@pytest.mark.parametrize(
    ("source_name", "source", "dependency_name"),
    [
        ("main.py", "import package.helper\n", "package/helper.py"),
        ("Main.java", "import com.example.Helper;\n", "com/example/Helper.java"),
        ("main.js", "import helper from './helper';\n", "helper.js"),
        ("main.ts", "import helper from './helper';\n", "helper.ts"),
        ("main.cpp", '#include "helper.hpp"\n', "helper.hpp"),
    ],
)
def test_dependency_graph_resolves_local_imports_for_supported_languages(
    tmp_path, source_name, source, dependency_name
):
    source_path = tmp_path / source_name
    dependency_path = tmp_path / dependency_name
    dependency_path.parent.mkdir(parents=True, exist_ok=True)
    dependency_path.write_text("", encoding="utf-8")
    source_path.write_text(source, encoding="utf-8")

    graph = CodeDependencyGraph()
    graph.add_file(str(source_path))

    assert graph.get_dependencies(str(source_path)) == [str(dependency_path)]

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
