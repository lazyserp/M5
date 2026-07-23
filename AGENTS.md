# AGENTS.md — Developer Guidelines & Step-by-Step Execution Roadmap for Project M5

This document serves as the master guide, style policy, and step-by-step roadmap for AI agents working in this workspace. It is structured to facilitate an incremental, secure, and robust "learn-by-building" implementation of Project M5 (Air-Gapped, On-Premise Enterprise AI System).

---

## 🛡️ User Profile & Tutoring Guidelines for Agents
*   **User Background:** Python & Java Backend Intern; aspiring Startup Founder. Does not have prior experience with ML inference engines, vector/graph databases, or VS Code extensions.
*   **Interaction Strategy (Mandatory for all Agent turns):**
    1.  **Do Not Rush Code:** Break every milestone down into micro-steps. Wait for execution approval between steps.
    2.  **Provide a Briefing:** Before editing any file or running a setup command, provide a clear, beginner-friendly briefing explaining *what* we are doing, *why* we are doing it, and define terms using both technical and layman terms.
    3.  **Include a CTO Pitch:** For every milestone, write a 2-sentence "CTO Pitch" that the user can use to explain that specific technical decision to a senior JPMC executive.
    4.  **Explain Code Changes:** Add inline comments or brief text explaining what each line of code or configuration does.

---

## 1. System Vision & Core Tech Stack
Project M5 is an air-gapped, high-security enterprise AI system designed to index corporate codebases (using AST-based Graph-RAG) and relational databases (via secure Text-to-SQL), serving them locally through open-source LLMs.

### Tech Stack:
- **Inference Layer:** Ollama (for CPU/local testing) / vLLM (for multi-GPU serving)
- **Base Models:** Qwen 2.5 Coder (7B/32B), DeepSeek-Coder-V2-Lite
- **Code Context Engine:** Tree-Sitter (AST parsing), Qdrant (vector db), NetworkX / Memgraph (dependency graph)
- **Database Layer:** PostgreSQL, psycopg2 (read-only sandboxed connection), regex & NeMo Guardrails
- **Backend API:** FastAPI (Python 3.10+)
- **Interface:** VS Code Extension (TypeScript)

---

## 2. Directory Structure
All developments must align with the following directory structure:
```text
M5/
├── .agents/
│   └── AGENTS.md             # This file
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers (chat, autocomplete, db-query)
│   │   ├── core/             # Config, security, database connectors
│   │   ├── rag/              # AST parser, chunker, Qdrant indexer, graph extractor
│   │   └── main.py           # FastAPI entrypoint
│   ├── tests/                # pytest tests for backend layers
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile            # Container definition for backend
├── extension/
│   ├── src/                  # VS Code Extension source (TypeScript)
│   ├── package.json          # Extension manifest
│   └── tsconfig.json         # TypeScript config
├── docker/
│   ├── docker-compose.yml    # Orchestration for FastAPI, Qdrant, Ollama, Postgres
│   └── init-db.sql           # Database schema seed
└── README.md
```

---

## 3. General Behavioral Guidelines for AI Agents
1. **Zero-Telemetry Rule:** Do not introduce any external telemetry, trackers, or network calls to external LLM providers (e.g., OpenAI, Anthropic, LangChain Hub). All logic must be local.
2. **Incremental Commit & Test:** Never execute multiple phases at once. Build one milestone, write unit tests in `backend/tests/`, verify it works, then proceed.
3. **Safety First:** Prioritize read-only transactions, security guardrails, and sandboxing in Phase 3. Never allow direct execution of unchecked LLM-generated SQL strings.
4. **Code Quality:** Write PEP 8 compliant, type-annotated Python, and modular TypeScript. Maintain existing codebase comments and docstrings.

---

## 4. End-to-End Execution Roadmap

### Phase 1: Local Micro-PoC (Days 1–7)
**Goal:** Serve a local LLM, set up a Python workspace, and build a terminal-based Q&A pipeline over a single source code file using basic vector retrieval.

#### Day 1: Setup & Local Inference Engine
- **Task:** Install Ollama on the local machine. Pull the Qwen 2.5 Coder 1.5B model (selected to run efficiently on Intel Integrated Graphics + 16GB system RAM). Verify response via Curl.
- **Commands:**
  ```bash
  # Install Ollama (Windows/macOS/Linux)
  # Download from https://ollama.com/download
  # Run the server and pull the model
  ollama run qwen2.5-coder:1.5b
  ```
- **Verification:** Run a test curl request to the Ollama server:
  ```powershell
  Invoke-RestMethod -Method Post -Uri "http://localhost:11434/api/generate" -ContentType "application/json" -Body '{"model": "qwen2.5-coder:1.5b", "prompt": "Write a python function to merge two sorted lists", "stream": false}'
  ```
- **Concept Spotlight:**
  - *Model Serving vs. Hugging Face pipelines:* Standard pipelines load the model weights directly into the Python process memory every execution, which is extremely slow. Engines like Ollama and vLLM run as separate background daemons, keeping model weights in VRAM, utilizing KV-caching, and using highly optimized C++ kernels (llama.cpp or vLLM PagedAttention) for high throughput.
  - *VRAM / System RAM Math for Low-Spec Hardware:* A 1.5B model in 4-bit quantization requires $\approx 1.2\text{ GB}$ memory. This runs efficiently directly on CPU/RAM for laptops lacking dedicated NVIDIA GPUs. A 7B model requires $\approx 4.5\text{ GB}$ RAM, which can throttle standard 16GB systems when combined with OS, IDE, and browser overhead.

#### Day 2: Python Environment & REST Client
- **Task:** Create `backend/` directory. Initialize virtual environment. Create a client script `backend/app/core/llm_client.py` that interfaces with Ollama's chat completions endpoint.
- **Commands:**
  ```bash
  mkdir backend
  cd backend
  python -m venv venv
  # Activate (Windows Powershell):
  .\venv\Scripts\Activate.ps1
  pip install requests pydantic
  ```
- **Code Snippet (`llm_client.py`):**
  ```python
  import requests
  from typing import Dict, Any

  class LocalLLMClient:
      def __init__(self, base_url: str = "http://localhost:11434"):
          self.chat_url = f"{base_url}/api/chat"

      def chat(self, system_prompt: str, user_prompt: str) -> str:
          payload = {
              "model": "qwen2.5-coder:1.5b",
              "messages": [
                  {"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}
              ],
              "stream": False
          }
          response = requests.post(self.chat_url, json=payload)
          response.raise_for_status()
          return response.json()["message"]["content"]
  ```

#### Day 3: Document Reading & Simple Chunking
- **Task:** Write `backend/app/rag/simple_splitter.py`. Create a script that reads any `.py` or `.cpp` file and splits it into character-based chunks of size 500, with 50 characters overlap.
- **Concept Spotlight:**
  - *Context Window Constraints:* LLMs have fixed input limits (e.g., 32k for Qwen 2.5). Chunking ensures large source repositories are digestible.
  - *Overlap:* Sliding windows prevent loss of context where semantic concepts (e.g., statements or arguments) are bisected by chunk boundaries.
- **Code Snippet (`simple_splitter.py`):**
  ```python
  from typing import List, Dict

  def chunk_file(file_path: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
      with open(file_path, 'r', encoding='utf-8') as f:
          content = f.read()
      
      chunks = []
      start = 0
      chunk_id = 0
      while start < len(content):
          end = min(start + chunk_size, len(content))
          chunk_text = content[start:end]
          chunks.append({
              "id": chunk_id,
              "text": chunk_text,
              "start_char": start,
              "end_char": end,
              "file": file_path
          })
          chunk_id += 1
          start += (chunk_size - overlap)
      return chunks
  ```

#### Day 4: Local Vector Embeddings
- **Task:** Write `backend/app/rag/embedder.py` using `sentence-transformers` to generate a 384-dimensional vector for each code chunk locally on CPU/GPU.
- **Commands:**
  ```bash
  pip install sentence-transformers torch
  ```
- **Code Snippet (`embedder.py`):**
  ```python
  from sentence_transformers import SentenceTransformer
  from typing import List

  class LocalEmbedder:
      def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
          # Loads model locally (cached under ~/.cache/huggingface)
          self.model = SentenceTransformer(model_name)

      def get_embeddings(self, texts: List[str]) -> List[List[float]]:
          embeddings = self.model.encode(texts, convert_to_numpy=True)
          return embeddings.tolist()
  ```
- **Concept Spotlight:**
  - *Vector Embeddings:* Text is compressed into a dense numerical array where similar concepts reside close to each other in vector space.
  - *Dimensions:* `all-MiniLM-L6-v2` produces a 384-dim vector, balancing CPU inference speed with semantic retention.

#### Day 5: In-Memory Vector Search
- **Task:** Write `backend/app/rag/memory_search.py` using NumPy. Store chunks and search them using cosine similarity.
- **Commands:**
  ```bash
  pip install numpy
  ```
- **Code Snippet (`memory_search.py`):**
  ```python
  import numpy as np
  from typing import List, Dict, Any

  def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
      dot = np.dot(v1, v2)
      norm_a = np.linalg.norm(v1)
      norm_b = np.linalg.norm(v2)
      if norm_a == 0.0 or norm_b == 0.0:
          return 0.0
      return float(dot / (norm_a * norm_b))

  class MemoryVectorStore:
      def __init__(self):
          self.registry: List[Dict[str, Any]] = []
          self.vectors: List[np.ndarray] = []

      def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
          for chunk, vector in zip(chunks, embeddings):
              self.registry.append(chunk)
              self.vectors.append(np.array(vector))

      def search(self, query_vector: List[float], top_k: int = 2) -> List[Dict[str, Any]]:
          q_vec = np.array(query_vector)
          scores = [cosine_similarity(q_vec, v) for v in self.vectors]
          ranked_indices = np.argsort(scores)[::-1][:top_k]
          
          results = []
          for idx in ranked_indices:
              results.append({
                  "chunk": self.registry[idx],
                  "score": scores[idx]
              })
          return results
  ```

#### Day 6: RAG Pipeline Integration
- **Task:** Create `backend/app/rag/rag_pipeline.py`. Combine the chunker, embedder, memory vector store, and local LLM client into a single CLI script that answers questions about a local python file.
- **Code Snippet (`rag_pipeline.py`):**
  ```python
  import sys
  from llm_client import LocalLLMClient
  from simple_splitter import chunk_file
  from embedder import LocalEmbedder
  from memory_search import MemoryVectorStore

  def run_rag(file_path: str, query: str):
      client = LocalLLMClient()
      embedder = LocalEmbedder()
      store = MemoryVectorStore()

      print("[+] Chunking file...")
      chunks = chunk_file(file_path)
      texts = [c["text"] for c in chunks]
      
      print("[+] Generating embeddings...")
      embeddings = embedder.get_embeddings(texts)
      store.add_chunks(chunks, embeddings)

      print("[+] Querying vector store...")
      query_vec = embedder.get_embeddings([query])[0]
      search_results = store.search(query_vec, top_k=2)

      context = "\n---\n".join([r["chunk"]["text"] for r in search_results])
      
      system_prompt = (
          "You are an on-premise code assistant. Answer the user's question using ONLY the provided code context. "
          "If the answer cannot be derived from the context, say 'I do not know'.\n\n"
          f"CONTEXT:\n{context}"
      )
      
      print(f"[+] Sending payload to local LLM...")
      answer = client.chat(system_prompt, query)
      print(f"\n[ANSWER]:\n{answer}")

  if __name__ == "__main__":
      # Run with: python rag_pipeline.py sample.py "How does the login work?"
      run_rag(sys.argv[1], sys.argv[2])
  ```

#### Day 7: Performance Profiling & Phase 1 Validation
- **Task:** Profile inference latency, tokens-per-second, RAM usage, and VRAM overhead.
- **Troubleshooting Hints:**
  - *CUDA OOM (Out Of Memory):* If your GPU hangs or throws `CUDA out of memory`, ensure you run Ollama with a quantized model (e.g., Q4_K_M). If running on CPU, close high-memory applications.
  - *Token Generation Latency:* If latency is >10s, verify Ollama isn't running purely on CPU. Check `nvidia-smi` to ensure the process runs on the GPU.

---

### Phase 2: AST Code Parsing & Vector RAG (Weeks 2–3)
**Goal:** Upgrade from simple character chunking to structural, syntax-aware chunking using Tree-Sitter, parse imports, and index chunks into a local Docker-based Qdrant vector database.

#### Milestone 2.1: AST Parsing with Tree-Sitter
- **Task:** Create `backend/app/rag/ast_parser.py`. Parse target files into Concrete/Abstract Syntax Trees using Tree-Sitter. Identify imports, classes, functions, and method block line spans.
- **Commands:**
  ```bash
  pip install tree-sitter tree-sitter-languages
  ```
- **Code Snippet (`ast_parser.py`):**
  ```python
  from tree_sitter_languages import get_parser
  from typing import List, Dict, Any

  class ASTParser:
      def __init__(self, language: str = "python"):
          self.parser = get_parser(language)

      def parse_code(self, code: str) -> List[Dict[str, Any]]:
          tree = self.parser.parse(bytes(code, "utf8"))
          root_node = tree.root_node
          blocks = []
          
          def traverse(node):
              # Check for function or class declarations
              if node.type in ["function_definition", "class_definition"]:
                  blocks.append({
                      "type": node.type,
                      "name": node.child_by_field_name("name").text.decode("utf8") if node.child_by_field_name("name") else "unknown",
                      "start_line": node.start_point[0] + 1,
                      "end_line": node.end_point[0] + 1,
                      "content": node.text.decode("utf8")
                  })
              for child in node.children:
                  traverse(child)

          traverse(root_node)
          return blocks
  ```
- **Concept Spotlight:**
  - *Why AST Chunks?* Text-based chunking cut functions in half, breaking class relationships. AST parsing splits code at functional boundaries (e.g. class declarations, complete method blocks), preserving scope.

#### Milestone 2.2: AST-Based Intelligent Chunker
- **Task:** Write `backend/app/rag/ast_chunker.py`. Build a logical chunker. If a class contains functions, chunk the functions individually while prefixing each with class context (e.g., `# Class: UserManager\ndef reset_password(): ...`).

#### Milestone 2.3: Indexing in Qdrant (Docker)
- **Task:** Setup a local Qdrant container and write `backend/app/rag/qdrant_indexer.py` to index AST chunks with metadata payloads (file path, line numbers, function signatures).
- **Commands:**
  ```bash
  # Launch Qdrant
  docker run -d -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant
  pip install qdrant-client
  ```
- **Code Snippet (`qdrant_indexer.py`):**
  ```python
  from qdrant_client import QdrantClient
  from qdrant_client.models import Distance, VectorParams, PointStruct

  class QdrantStore:
      def __init__(self, host: str = "localhost", port: int = 6333):
          self.client = QdrantClient(host=host, port=port)
          self.collection_name = "codebase_vectors"

      def init_collection(self, vector_size: int = 384):
          if not self.client.collection_exists(self.collection_name):
              self.client.create_collection(
                  collection_name=self.collection_name,
                  vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
              )

      def upload_chunks(self, chunks: list, embeddings: list):
          points = []
          for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
              points.append(
                  PointStruct(
                      id=idx,
                      vector=vector,
                      payload={
                          "content": chunk["content"],
                          "type": chunk["type"],
                          "name": chunk["name"],
                          "start_line": chunk["start_line"],
                          "end_line": chunk["end_line"]
                      }
                  )
              )
          self.client.upsert(collection_name=self.collection_name, points=points)
  ```
- **Concept Spotlight:**
  - *HNSW Graphs:* Qdrant searches vectors using Hierarchical Navigable Small World graphs, enabling search speeds of under 10ms for millions of chunks without linear brute-force scanning.

#### Milestone 2.4: Code Dependency Graph Engine
- **Task:** Write `backend/app/rag/dependency_graph.py` using `networkx`. Extract import paths from files, build a directed dependency graph. If file `auth.py` imports `db.py`, create a directed edge `auth.py -> db.py`.
- **Concept Spotlight:**
  - *Graph RAG:* When a query refers to a class `UserManager`, vector search finds its definition. The dependency graph then traverses related imports and fetches `DbConnection` from `db.py` to form a comprehensive contextual prompt.

#### Milestone 2.5: Phase 2 Verification & Troubleshooting
- **Troubleshooting Hints:**
  - *C Compiler Errors on Tree-Sitter:* If installation fails on Windows, install Visual Studio Build Tools with C++ compiler workload.
  - *Qdrant Payload Mismatches:* If query payloads return empty, verify that payload fields are not being overwritten by incorrect indexing steps.

---

### Phase 3: Text-to-SQL & Security Guardrails (Weeks 4–5)
**Goal:** Ingest database schema (DDL), translate natural language to SQL, execute it in a sandboxed, read-only PostgreSQL instance, and run guardrails to prevent malicious modifications and data leaks.

#### Milestone 3.1: DDL Ingestion & SQL Context Generator
- **Task:** Create `backend/app/core/db_schema.py`. Extract table schemas, indexes, and primary/foreign keys from a live database or a static `.sql` DDL file, and format it as markdown schema descriptions.
- **Code Snippet (`db_schema.py`):**
  ```python
  def get_schema_context() -> str:
      # In production, query pg_catalog to get actual table DDLs.
      # Hardcoded schema representation for validation:
      return """
      TABLE users (
          id INT PRIMARY KEY,
          username VARCHAR(50) UNIQUE,
          email VARCHAR(100),
          created_at TIMESTAMP
      );
      TABLE transactions (
          id INT PRIMARY KEY,
          user_id INT REFERENCES users(id),
          amount DECIMAL(10,2),
          status VARCHAR(20),
          timestamp TIMESTAMP
      );
      """
  ```

#### Milestone 3.2: Execution Sandboxing
- **Task:** Create `backend/app/core/db_sandbox.py` using `psycopg2`. Execute queries inside a read-only transaction pool, setting strict command timeouts.
- **Commands:**
  ```bash
  pip install psycopg2-binary
  ```
- **Code Snippet (`db_sandbox.py`):**
  ```python
  import psycopg2
  from psycopg2 import sql
  from typing import List, Dict, Any

  class SandboxedDBSession:
      def __init__(self, dsn: str):
          self.dsn = dsn

      def execute_readonly_query(self, sql_query: str, timeout_ms: int = 5000) -> List[Dict[str, Any]]:
          conn = psycopg2.connect(self.dsn)
          conn.autocommit = False
          cursor = conn.cursor()
          
          results = []
          try:
              # Set execution timeout and enforce read-only
              cursor.execute(f"SET Statement_timeout = {timeout_ms};")
              cursor.execute("SET TRANSACTION READ ONLY;")
              cursor.execute(sql_query)
              
              columns = [desc[0] for desc in cursor.description] if cursor.description else []
              for row in cursor.fetchall():
                  results.append(dict(zip(columns, row)))
              
              conn.commit()  # Commits the read-only transaction
          except Exception as e:
              conn.rollback()
              raise e
          finally:
              cursor.close()
              conn.close()
          return results
  ```

#### Milestone 3.3: Guardrails & Query Sanitation
- **Task:** Create `backend/app/core/guardrails.py`. Intercept generated SQL strings before DB execution. Check for blocked SQL keywords, SQL injection tokens, and drop requests.
- **Code Snippet (`guardrails.py`):**
  ```python
  import re

  BLOCKED_KEYWORDS = [
      r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b", 
      r"\bTRUNCATE\b", r"\bALTER\b", r"\bGRANT\b", r"\bREVOKE\b"
  ]

  def validate_sql(query: str) -> bool:
      clean_query = query.strip().upper()
      for pattern in BLOCKED_KEYWORDS:
          if re.search(pattern, clean_query):
              return False
      # Block double hyphens (inline comments) often used in SQL injections
      if "--" in query:
          return False
      return True
  ```
- **Concept Spotlight:**
  - *SQL Injection via LLM:* Prompt injection occurs when user queries trick the model into outputting destructive queries (e.g. user asks "Show all users; DROP TABLE transactions;"). Static regex validation + enforcing database role privileges (`GRANT SELECT ON ...`) ensures defensive security.

#### Milestone 3.4: Unified Text-to-SQL API
- **Task:** Implement the FastAPI router in `backend/app/api/endpoints/query_db.py`. Integrate schema context, prompt the LLM to output ONLY raw SQL, validate it via guardrails, and execute it using the read-only sandbox.

---

### Phase 4: VS Code Extension & Dockerized Air-Gap Package (Weeks 6–8)
**Goal:** Create a FastAPI backend supporting server-sent event (SSE) streaming, construct a VS Code Extension for inline completions (FIM) and chat, and package the complete system into docker-compose for air-gapped server installation.

#### Milestone 4.1: Unified FastAPI Stream Engine
- **Task:** Implement `backend/app/main.py`. Support stream responses using FastAPI's `StreamingResponse` for chatbot completions and standard JSON completions for autocomplete.
- **Commands:**
  ```bash
  pip install fastapi uvicorn sse-starlette
  ```
- **Code Snippet (`main.py`):**
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  from fastapi.responses import StreamingResponse
  import json
  import requests

  app = FastAPI(title="Project M5 Backend API")

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )

  @app.post("/api/chat")
  async def chat_endpoint(payload: dict):
      def stream_generator():
          url = "http://localhost:11434/api/chat"
          response = requests.post(url, json={**payload, "stream": True}, stream=True)
          for chunk in response.iter_lines():
              if chunk:
                  decoded = chunk.decode("utf-8")
                  data = json.loads(decoded)
                  content = data.get("message", {}).get("content", "")
                  yield f"data: {json.dumps({'content': content})}\n\n"
      return StreamingResponse(stream_generator(), media_type="text/event-stream")
  ```

#### Milestone 4.2: VS Code Extension Chat Panel
- **Task:** Set up a Node/TypeScript workspace under `extension/`. Install dependencies. Define a Webview panel that opens inside the VS Code editor sidebar.
- **Commands:**
  ```bash
  cd extension
  # Initialize node package
  npm init -y
  # Install extension development dependencies
  npm install typescript vscode-test-electron --save-dev
  ```
- **Code Snippet (Webview chat panel launcher in `extension/src/extension.ts`):**
  ```typescript
  import * as vscode from 'vscode';

  export function activate(context: vscode.ExtensionContext) {
      let disposable = vscode.commands.registerCommand('m5.openChat', () => {
          const panel = vscode.window.createWebviewPanel(
              'm5Chat',
              'Project M5 Chat',
              vscode.ViewColumn.Two,
              { enableScripts: true }
          );

          panel.webview.html = getWebviewContent();
      });
      context.subscriptions.push(disposable);
  }

  function getWebviewContent() {
      return `<!DOCTYPE html>
      <html lang="en">
      <head>
          <style>body { font-family: sans-serif; padding: 10px; color: #fff; }</style>
      </head>
      <body>
          <h3>M5 Code Assistant</h3>
          <input type="text" id="query" placeholder="Ask about your codebase..." style="width: 100%;" />
          <button onclick="sendQuery()">Submit</button>
          <div id="output"></div>
          <script>
              const vscode = acquireVsCodeApi();
              function sendQuery() {
                  const val = document.getElementById('query').value;
                  // Handle Fetch request to localhost:8000/api/chat here
              }
          </script>
      </body>
      </html>`;
  }
  ```

#### Milestone 4.3: Inline Autocomplete Engine
- **Task:** Bind an `InlineCompletionItemProvider` in `extension/src/extension.ts` using FIM format targeting Ollama's code completion model.
- **Concept Spotlight:**
  - *FIM (Fill-in-the-Middle):* Code completions require knowing what text precedes the cursor (Prefix) and what follows it (Suffix). Code models are trained with special delimiters: `<fim_prefix> prefix_code <fim_suffix> suffix_code <fim_middle>`. The model naturally fills in the gap.
- **Code Snippet (`extension.ts`):**
  ```typescript
  vscode.languages.registerInlineCompletionItemProvider(
      { pattern: '**/*' },
      {
          async provideInlineCompletionItems(document, position, context, token) {
              const prefix = document.getText(new vscode.Range(new vscode.Position(0, 0), position));
              const suffix = document.getText(new vscode.Range(position, document.positionAt(document.getText().length)));
              
              // Format FIM payload
              const prompt = `<fim_prefix>${prefix}<fim_suffix>${suffix}<fim_middle>`;
              
              // Fetch completion from backend
              const response = await fetch("http://localhost:8000/api/autocomplete", {
                  method: "POST",
                  body: JSON.stringify({ prompt })
              });
              const data = await response.json();
              
              return [new vscode.InlineCompletionItem(data.completion)];
          }
      }
  );
  ```

#### Milestone 4.4: Dockerized Air-Gap Package
- **Task:** Create `docker/docker-compose.yml` to stitch the components together. Set up host volume bindings for the models and indexing database directory so that no run-time downloads are required.
- **Code Snippet (`docker-compose.yml`):**
  ```yaml
  version: '3.8'

  services:
    ollama:
      image: ollama/ollama:latest
      container_name: m5-ollama
      ports:
        - "11434:11434"
      volumes:
        - ollama_storage:/root/.ollama
      deploy:
        resources:
          reservations:
            devices:
              - driver: nvidia
                count: all
                capabilities: [gpu]

    qdrant:
      image: qdrant/qdrant:latest
      container_name: m5-qdrant
      ports:
        - "6333:6333"
      volumes:
        - qdrant_storage:/qdrant/storage

    postgres:
      image: postgres:15
      container_name: m5-postgres
      environment:
        POSTGRES_DB: m5_db
        POSTGRES_USER: m5_admin
        POSTGRES_PASSWORD: securepassword123
      ports:
        - "5432:5432"
      volumes:
        - pg_storage:/var/lib/postgresql/data

    backend:
      build:
        context: ../backend
      container_name: m5-backend
      ports:
        - "8000:8000"
      depends_on:
        - ollama
        - qdrant
        - postgres
      environment:
        - OLLAMA_HOST=http://ollama:11434
        - QDRANT_HOST=qdrant
        - DB_DSN=postgresql://m5_admin:securepassword123@postgres:5432/m5_db

  volumes:
    ollama_storage:
    qdrant_storage:
    pg_storage:
  ```
- **Concept Spotlight:**
  - *NVIDIA Container Toolkit:* The `gpu` reservation section maps underlying physical GPUs into the Docker container. This is crucial for maintaining sub-100ms inference execution on-prem.

#### Milestone 4.5: Offline Deployment Validation
- **Troubleshooting Hints:**
  - *Docker GPU Reservation Fails:* Ensure the NVIDIA Container Toolkit is installed on the host machine. If not present, remove the `deploy.resources.reservations` block to fall back to CPU serving (highly latent).
  - *Extension Connection Refused:* In Windows development, if the container runs backend on port 8000, ensure WSL/Docker handles port bindings correctly.

---

## 5. Verification Checklist & Milestones
- [ ] Phase 1: Local PoC generates code completions on single python files without external telemetry.
- [ ] Phase 2: Chunks are generated strictly respecting functional AST nodes; retrieval uses cosine similarity inside Docker Qdrant.
- [ ] Phase 3: DB schemas can be queried via Text-to-SQL. Blocked keyword list blocks modifying statements (`DROP`, `TRUNCATE`) successfully.
- [ ] Phase 4: VS Code extensions successfully retrieve inline completions from the local endpoint and load Webviews without console errors.
