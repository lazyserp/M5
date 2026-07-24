from typing import List, Dict, Any

class ASTChunker:
    """
    A modular, language-agnostic chunker that processes AST code blocks.
    
    It matches parent-child relationships (e.g. methods inside a class) 
    using line range containment math and prepends parent context to child blocks.
    """
    def chunk_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes syntax blocks and adds parent class prefix tags to inner methods.
        """
        sorted_blocks = sorted(
            blocks,
            key=lambda x: (x["start_line"], -(x["end_line"] - x["start_line"]))
        )
        
        chunks = []
        
        for block in sorted_blocks:
            parent_class = None
            is_func = "function" in block["type"] or "method" in block["type"]
            
            if is_func:
                for potential_parent in sorted_blocks:
                    is_class = "class" in potential_parent["type"] or "interface" in potential_parent["type"]
                    if is_class:
                        if (potential_parent["start_line"] <= block["start_line"] and 
                            potential_parent["end_line"] >= block["end_line"]):
                            parent_class = potential_parent
                            break
            
            content = block["content"]
            
            if parent_class:
                file_ext = block.get("file", "").split(".")[-1].lower()
                comment_style = "//" if file_ext in ["java", "cpp", "c", "h", "js", "ts"] else "#"
                content = f"{comment_style} Class Context: {parent_class['name']}\n{content}"
            
            chunks.append({
                "type": block["type"],
                "name": block["name"],
                "start_line": block["start_line"],
                "end_line": block["end_line"],
                "content": content,
                "file": block.get("file", "")
            })
            
        return chunks
