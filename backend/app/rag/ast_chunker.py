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
        
        Parameters:
        - blocks (List[Dict[str, Any]]): The list of parsed syntax blocks from ASTParser.
        
        Returns:
        - List[Dict[str, Any]]: Chunks with structural prefixes.
        """
        # 1. Sort the blocks by start line. 
        # If two blocks start on the same line, sort by largest block size first 
        # (meaning the class declaration will come before the constructor).
        sorted_blocks = sorted(
            blocks,
            key=lambda x: (x["start_line"], -(x["end_line"] - x["start_line"]))
        )
        
        chunks = []
        
        for block in sorted_blocks:
            parent_class = None
            
            # Check if this block is a function/method
            # Works for Python ("function_definition"), Java ("method_declaration"), and C++ ("function_definition")
            is_func = "function" in block["type"] or "method" in block["type"]
            
            if is_func:
                # 2. Find if this function is physically located inside a class.
                # We do this by searching for any class block that wraps around this function's lines.
                for potential_parent in sorted_blocks:
                    is_class = "class" in potential_parent["type"] or "interface" in potential_parent["type"]
                    if is_class:
                        # Check if function lines fall entirely inside the class start/end line range
                        if (potential_parent["start_line"] <= block["start_line"] and 
                            potential_parent["end_line"] >= block["end_line"]):
                            parent_class = potential_parent
                            break # Found the enclosing class, stop searching
            
            content = block["content"]
            
            # 3. If we found a parent class, prefix the function content with the class name!
            if parent_class:
                # Support multi-language comment styles dynamically based on file extension:
                # - Java, C++, JS, TS use '//'
                # - Python uses '#'
                file_ext = block.get("file", "").split(".")[-1].lower()
                comment_style = "//" if file_ext in ["java", "cpp", "c", "h", "js", "ts"] else "#"
                
                content = f"{comment_style} Class Context: {parent_class['name']}\n{content}"
            
            # 4. Save the chunk with the context-grounded code content
            chunks.append({
                "type": block["type"],
                "name": block["name"],
                "start_line": block["start_line"],
                "end_line": block["end_line"],
                "content": content,
                "file": block.get("file", "")
            })
            
        return chunks
