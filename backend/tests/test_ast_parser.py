import os
import sys

# Append the parent (backend/) directory to the search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag.ast_parser import ASTParser

def test_ast_parser():
    # parse llm_client.py file to test the parser!
    target_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/core/llm_client.py'))
    
    print(f"[+] Reading file: {target_file}")
    with open(target_file, "r", encoding="utf-8") as f:
        code_content = f.read()

    # Initialize the ASTParser for Python
    print("[+] Initializing ASTParser for Python...")
    parser = ASTParser(language_name="python")

    #  Parse the code
    print("[+] Parsing code content into AST blocks...")
    blocks = parser.parse_code(code_content)

    print(f"[SUCCESS] Extracted {len(blocks)} code blocks!\n")

    #  Print out details of each extracted code block
    for idx, block in enumerate(blocks):
        print(f"--- BLOCK {idx} ({block['type'].upper()}): {block['name']} ---")
        print(f"Lines: {block['start_line']} to {block['end_line']}")
        # Print a preview of the content (first 3 lines of code)
        content_lines = block["content"].splitlines()
        preview = "\n".join(content_lines[:3])
        
        if len(content_lines) > 3:
            preview += "\n..."
        print(f"Content Preview:\n{preview}")
        print("-" * 50)

if __name__ == "__main__":
    test_ast_parser()
