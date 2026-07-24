# Write your Code Dependency Graph Engine here!
# Goal: Scan source code files for imports and build a directed graph in NetworkX.
import os
import re
import networkx as nx
from typing import List , Dict , Any

class CodeDependencyGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.import_patterns = {
                    "py" : [
                        re.compile(r"^\s*import\s+([a-zA-Z0-9_\.]+)"),
                        re.compile(r"^\s*from\s+([a-zA-Z0-9_\.]+)\s+import")
                    ]
                }

    def add_file(self,file_path : str):
        file_path  = os.path.abspath(file_path)
        self.graph.add_node(file_path)

        ext = file_path.split(".")[-1].lower()
        patterns = self.import_patterns.get(ext,[])
        if not patterns:
            return

        lines = ""

        try:
            with open(file_path,"r",encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return
        
        for line in lines:
            for pattern in patterns:
                match = pattern.match(line)
                if match:
                      # Capture the matched import name
                    imported_module = match.group(1)

                    # Call a helper method to find the actual file path on disk
                    resolved_path = self._resolve_import_path(file_path, imported_module)

                    if resolved_path:
                        self.graph.add_node(resolved_path)
                        # Connect them: file_path -> resolved_path
                        self.graph.add_edge(file_path,resolved_path)


    def _resolve_import_path(self, current_file: str, imported_module: str) -> str | None:
        # Get the directory where current_file is located
        current_dir = os.path.dirname(os.path.abspath(current_file))

        # Replace dots with slashes (e.g. "app.core" becomes "app/core")
        clean_import = imported_module.replace(".", "/")

        # Keep walking up the directory tree towards the drive root
        while True:
            # Check if the imported module file exists in this directory level
            candidate_path = os.path.abspath(os.path.join(current_dir, clean_import + ".py"))
            if os.path.exists(candidate_path):
                return candidate_path

            # Move up one directory level
            parent_dir = os.path.dirname(current_dir)
            
            # If we hit the drive root (where parent_dir is the same as current_dir), stop
            if parent_dir == current_dir:
                break
                
            current_dir = parent_dir

        # If the file doesn't exist anywhere in the project tree, return None
        return None



    def get_dependencies(self, file_path: str) -> List[str]:
        # Convert path to absolute to avoid mismatch
        file_path = os.path.abspath(file_path)
        
        # If the file has been parsed in our graph, return its direct connections (successors)
        if file_path in self.graph:
            return list(self.graph.successors(file_path))
        return []
