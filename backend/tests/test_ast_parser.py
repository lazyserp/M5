import os
import sys

# Append parent (backend/) directory to search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# pyrefly: ignore [missing-import]
from app.rag.parsers.ast_parser import ASTParser

def test_ast_parser():
    target_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/core/llm_client.py'))
    
    print(f"[+] Reading file: {target_file}")
    with open(target_file, "r", encoding="utf-8") as f:
        code_content = f.read()

    print("[+] Initializing ASTParser for Python...")
    parser = ASTParser(language_name="python")

    print("[+] Parsing code content into AST blocks...")
    blocks = parser.parse_code(code_content)

    print(f"[SUCCESS] Extracted {len(blocks)} code blocks!\n")

    for idx, block in enumerate(blocks):
        print(f"--- BLOCK {idx} ({block['type'].upper()}): {block['name']} ---")
        print(f"Lines: {block['start_line']} to {block['end_line']}")
        content_lines = block["content"].splitlines()
        preview = "\n".join(content_lines[:3])
        
        if len(content_lines) > 3:
            preview += "\n..."
        print(f"Content Preview:\n{preview}")
        print("-" * 50)

if __name__ == "__main__":
    test_ast_parser()
