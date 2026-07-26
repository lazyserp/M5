import os
import re
import networkx as nx
from typing import List, Dict, Any

class CodeDependencyGraph:
    """
    Codebase import dependency extractor using NetworkX directed graphs.
    """
    def __init__(self):
        self.graph = nx.DiGraph()
        self.import_patterns = {
            "py": [
                re.compile(r"^\s*import\s+([a-zA-Z0-9_\.]+)"),
                re.compile(r"^\s*from\s+([a-zA-Z0-9_\.]+)\s+import")
            ],
            "java": [
                re.compile(r"^\s*import\s+([a-zA-Z0-9_\.]+);")
            ],
            "js": [
                re.compile(r"^\s*import\s+.*?\s+from\s+['\"](.*?)['\"]"),
                re.compile(r"^\s*const\s+.*?\s*=\s*require\(['\"](.*?)['\"]\)")
            ],
            "ts": [
                re.compile(r"^\s*import\s+.*?\s+from\s+['\"](.*?)['\"]"),
                re.compile(r"^\s*const\s+.*?\s*=\s*require\(['\"](.*?)['\"]\)")
            ],
            "cpp": [
                re.compile(r'^\s*#include\s+["<]([a-zA-Z0-9_\.\/\\]+)[">]')
            ],
            "h": [
                re.compile(r'^\s*#include\s+["<]([a-zA-Z0-9_\.\/\\]+)[">]')
            ]
        }

    def add_file(self, file_path: str):
        file_path = os.path.abspath(file_path)
        self.graph.add_node(file_path)

        ext = file_path.split(".")[-1].lower()
        patterns = self.import_patterns.get(ext, [])
        if not patterns:
            return

        lines = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return
        
        for line in lines:
            for pattern in patterns:
                match = pattern.match(line)
                if match:
                    imported_module = match.group(1)
                    resolved_path = self._resolve_import_path(file_path, imported_module)
                    if resolved_path:
                        self.graph.add_node(resolved_path)
                        self.graph.add_edge(file_path, resolved_path)

    def _resolve_import_path(self, current_file: str, imported_module: str) -> str | None:
        current_dir = os.path.dirname(os.path.abspath(current_file))
        clean_import = imported_module.replace(".", "/")

        while True:
            candidate_path = os.path.abspath(os.path.join(current_dir, clean_import + ".py"))
            if os.path.exists(candidate_path):
                return candidate_path

            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                break
                
            current_dir = parent_dir

        return None

    def get_dependencies(self, file_path: str) -> List[str]:
        file_path = os.path.abspath(file_path)
        if file_path in self.graph:
            return list(self.graph.successors(file_path))
        return []
