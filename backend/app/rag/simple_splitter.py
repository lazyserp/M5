
from typing import List , Dict , Any

def chunk_file(file_path : str ,chunk_size:int = 500 , overlap:int = 50 ) -> List[Dict[str,Any]]:
    with open(file_path,'r',encoding='utf-8') as f:
        content = f.read()

        chunks = []
        start = 0
        chunk_id = 0

        while start < len(content):
            end = min(start + chunk_size,len(content))
            chunk_text = content[start:end]

            chunk_dict = {
                            "id": chunk_id,
                            "text": chunk_text,
                            "start_char": start,
                            "end_char": end,
                            "file": file_path
                        }

            chunks.append(chunk_dict)

            chunk_id += 1
            start += (chunk_size - overlap)

    return chunks