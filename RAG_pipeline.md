sequenceDiagram
    autonumber
    actor Dev as Developer Terminal
    participant RAG as rag_pipeline.py
    participant Split as simple_splitter.py
    participant Emb as embedder.py
    participant DB as memory_search.py
    participant Llama as Ollama API (Qwen 1.5B)

    Dev->>RAG: Runs python rag_pipeline.py llm_client.py "What is the default base_url?"
    
    Note over RAG,Split: PHASE 1: INGESTION (Chunking)
    RAG->>Split: Reads llm_client.py and splits it
    Split-->>RAG: Returns List of Chunks (Text + Metadata)
    
    Note over RAG,Emb: PHASE 2: SEMANTIC ENCODING
    RAG->>Emb: Converts chunk texts to coordinates
    Emb-->>RAG: Returns List of 384-Dimensional Vectors
    
    Note over RAG,DB: PHASE 3: INDEXING
    RAG->>DB: Saves Chunks and Vectors in Parallel lists
    
    Note over RAG,Emb: PHASE 4: RETRIEVAL (Search)
    RAG->>Emb: Converts query "What is the default base_url?" to a Vector
    Emb-->>RAG: Returns Query Vector
    RAG->>DB: Searches for top 2 matches of Query Vector
    DB->>DB: Calculates Cosine Similarity (vector angles) for all chunks
    DB-->>RAG: Returns Top 2 Chunks (Chunk 0 & Chunk 1)
    
    Note over RAG,Llama: PHASE 5: CONTEXTUAL GENERATION
    RAG->>RAG: Combines Chunk 0 & Chunk 1 into "CONTEXT" block
    RAG->>RAG: Builds System Prompt: "Answer using ONLY this CONTEXT..."
    RAG->>Llama: Sends System Prompt + User Query to Ollama Local Server
    Llama-->>RAG: Generates: "The default base_url is 'http://localhost:11434'"
    
    RAG->>Dev: Prints Final Answer to Terminal
