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
                    resolved_path = self._resolve_import_path(file_path, imported_module, ext)
                    if resolved_path:
                        self.graph.add_node(resolved_path)
                        self.graph.add_edge(file_path, resolved_path)

    def _resolve_import_path(
        self, current_file: str, imported_module: str, language: str | None = None
    ) -> str | None:
        """Return a local source file matching an import in ``current_file``.

        Each language has a different import-to-file convention.  Python and
        Java use dotted module names, JavaScript/TypeScript use relative paths,
        and C/C++ includes normally already contain a file extension.
        """
        current_dir = os.path.dirname(os.path.abspath(current_file))
        language = language or os.path.splitext(current_file)[1].lstrip(".").lower()

        if language in {"py", "java"}:
            clean_import = imported_module.replace(".", os.sep)
            extensions = [".py"] if language == "py" else [".java"]
            include_index = language == "py"
        elif language in {"js", "ts"}:
            # Only relative/absolute paths can reliably refer to local files.
            # Package imports such as "react" are intentionally ignored.
            if not imported_module.startswith((".", "/", "\\")):
                return None
            clean_import = imported_module
            extensions = [".js", ".jsx"] if language == "js" else [".ts", ".tsx", ".js"]
            include_index = True
        elif language in {"cpp", "h"}:
            clean_import = imported_module
            extensions = ["", ".h", ".hpp", ".cpp", ".cc", ".cxx"]
            include_index = False
        else:
            return None

        while True:
            for candidate in self._candidate_paths(
                current_dir, clean_import, extensions, include_index
            ):
                if os.path.isfile(candidate):
                    return candidate

            # Relative JS/TS imports must be resolved from the importing file's
            # folder; walking upwards would incorrectly match unrelated files.
            if language in {"js", "ts"}:
                break

            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:
                break
            current_dir = parent_dir

        return None

    @staticmethod
    def _candidate_paths(
        base_dir: str, module_path: str, extensions: List[str], include_index: bool
    ) -> List[str]:
        """Build possible local file paths without assuming one extension."""
        base_path = os.path.abspath(os.path.join(base_dir, module_path))
        candidates = [base_path]

        if not os.path.splitext(base_path)[1]:
            candidates.extend(base_path + extension for extension in extensions if extension)

        if include_index:
            candidates.extend(
                os.path.join(base_path, "index" + extension)
                for extension in extensions
                if extension
            )

        return candidates

    def get_dependencies(self, file_path: str) -> List[str]:
        file_path = os.path.abspath(file_path)
        if file_path in self.graph:
            return list(self.graph.successors(file_path))
        return []
