from typing import List, Dict, Any

def chunk_file(file_path: str, chunk_lines: int = 40, line_overlap: int = 5) -> List[Dict[str, Any]]:
    """
    Line-aware chunker for non-AST files (SQL, Markdown, YAML, JSON, TXT, etc.)
    Preserves exact 1-indexed start_line and end_line bounds for every chunk.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return []

    if not lines:
        return []

    chunks = []
    chunk_id = 0
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        start_line = i + 1
        end_line = min(i + chunk_lines, total_lines)
        chunk_lines_text = lines[i:end_line]
        chunk_text = "".join(chunk_lines_text)

        chunks.append({
            "id": chunk_id,
            "text": chunk_text,
            "content": chunk_text,
            "start_line": start_line,
            "end_line": end_line,
            "file": file_path
        })

        chunk_id += 1
        i += (chunk_lines - line_overlap)
        if i >= total_lines:
            break

    return chunks
