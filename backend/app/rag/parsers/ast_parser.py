import importlib
from typing import List, Dict, Any
from tree_sitter import Language, Parser

# Dictionary mapping language names to their tree-sitter block node types.
LANGUAGE_BLOCK_TYPES = {
    "python": ["function_definition", "class_definition", "async_function_definition"],
    "java": ["method_declaration", "class_declaration", "interface_declaration", "record_declaration", "enum_declaration", "constructor_declaration"],
    "cpp": ["function_definition", "class_specifier", "struct_specifier", "namespace_definition"],
    "javascript": ["function_declaration", "class_declaration", "method_definition", "arrow_function"],
    "typescript": ["function_declaration", "class_declaration", "method_definition", "arrow_function", "interface_declaration", "type_alias_declaration", "enum_declaration"],
}

class ASTParser:
    """
    A highly modular AST parser using Tree-Sitter.
    Dynamically loads grammar packages based on the target language name.
    """
    def __init__(self, language_name: str = "python"):
        self.language_name = language_name.lower().strip()
        lang_obj = self._load_language(self.language_name)
        self.parser = Parser(lang_obj)

    def _load_language(self, lang_name: str) -> Language:
        name_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "c++": "cpp",
        }
        clean_name = name_map.get(lang_name, lang_name)
        module_name = f"tree_sitter_{clean_name}"

        try:
            lang_module = importlib.import_module(module_name)
            return Language(lang_module.language())
        except ImportError:
            raise ImportError(
                f"The grammar package '{module_name}' is not installed globally.\n"
                f"Please run 'pip install {module_name}' to enable parsing for '{lang_name}' files."
            )

    def parse_code(self, code: str) -> List[Dict[str, Any]]:
        """
        Parses source code text and returns structural code blocks (functions, classes, etc.)
        along with their metadata and contents.
        """
        tree = self.parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        blocks = []

        target_types = LANGUAGE_BLOCK_TYPES.get(self.language_name, ["function_definition", "class_definition"])

        def traverse(node):
            if node.type in target_types:
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = bytes(code, "utf8")[name_node.start_byte : name_node.end_byte].decode("utf8")
                else:
                    name = node.type

                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                content = bytes(code, "utf8")[node.start_byte : node.end_byte].decode("utf8")

                blocks.append({
                    "type": node.type,
                    "name": name,
                    "start_line": start_line,
                    "end_line": end_line,
                    "content": content
                })

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return blocks
