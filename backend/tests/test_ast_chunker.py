import os
import sys

# Appending backend/ folder to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag.ast_parser import ASTParser
from app.rag.ast_chunker import ASTChunker

def test_ast_chunker():
    # Target client script as the test subject
    target_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/core/llm_client.py'))
    
    print(f"[+] Loading code content from: {target_file}")
    with open(target_file, "r", encoding="utf-8") as f:
        code_content = f.read()

    # Parse into raw AST blocks
    parser = ASTParser(language_name="python")
    raw_blocks = parser.parse_code(code_content)
    
    # We tag each block with the file name so the chunker can resolve the comment style
    for b in raw_blocks:
        b["file"] = target_file

    # 2. Run our Chunker
    print("[+] Running ASTChunker to resolve parent-child context scopes...")
    chunker = ASTChunker()
    chunks = chunker.chunk_blocks(raw_blocks)

    print(f"[SUCCESS] Processed {len(chunks)} code chunks!\n")

    # 3. Print the results to verify prefixing
    for idx, chunk in enumerate(chunks):
        print(f"--- CHUNK {idx} ({chunk['type'].upper()}): {chunk['name']} ---")
        print(f"Lines: {chunk['start_line']} to {chunk['end_line']}")
        
        # Display the first 4 lines of the chunk content
        lines = chunk["content"].splitlines()
        preview = "\n".join(lines[:4])
        if len(lines) > 4:
            preview += "\n..."
        print(f"Code Content:\n{preview}")
        print("-" * 50)

if __name__ == "__main__":
    test_ast_chunker()
