# M5 Context Engine for LLMs


M5 helps engineering organizations analyze, onboard, and investigate legacy or sensitive codebases without sending source code or prompts to external AI providers. All answers are grounded in exact repository snapshots with verifiable file paths and line-range citations.

---

##  Architecture & System Flow

```mermaid
flowchart TD
    subgraph Client ["VS Code Extension"]
        Developer["Developer Query"]
        Webview["Rich Markdown Chat Panel"]
    end

    subgraph Backend ["FastAPI Core Server"]
        API["FastAPI Orchestrator"]
        Parser["AST Parser & Ingestion Service"]
        Embedder["Local Embedder"]
        LLMSelector{"LLM Selector"}
    end

    subgraph Storage ["On-Premise Storage & Vector DB"]
        Qdrant[("Qdrant Vector Database")]
        GitRepo[("Workspace Repositories")]
    end

    subgraph Models ["LLM Engine (Customer Controlled)"]
        Ollama["Ollama Local Model (Default)"]
        LLM["LLM Service (Optional)"]
    end

    %% Ingestion Flow
    GitRepo -->|"AST Extraction"| Parser
    Parser -->|"Structural Chunks"| Embedder
    Embedder -->|"Vector Embeddings"| Qdrant

    %% Query Flow
    Developer -->|"Send Query"| API
    API -->|"Vector Search"| Qdrant
    Qdrant -->|"Retrieved Context & Dependency Chunks"| API
    API --> LLMSelector
    
    LLMSelector -->|"No API Key"| Ollama
    LLMSelector -->|"LLM_API_KEY Set"| OpenAI, Claude ,Kimi

    Ollama -->|"Contextual Answer"| API
    LLM -->|"Contextual Answer"| API
    
    API -->|"Grounded Answer + Exact Citations"| Webview
```

---

##  Key Features

-  **Customer-Controlled & Air-Gapped Ready**: Operates on local models (Ollama) or internal infrastructure with zero external telemetry.
-  **Exact Evidence & Citations**: Every substantive answer includes repository file paths and exact line ranges.
-  **Graph-RAG & AST Structural Context**: Ingests codebases using Tree-sitter/AST parsing and expands graph dependencies for neighboring code context.
-  **Rich IDE Experience**: VS Code Extension webview with rich GitHub-Flavored Markdown (headers, bolding, italics, bullet lists, code blocks with copy buttons, and citation pills).
-  **Automatic Model Fallback**: Uses local Ollama (`qwen2.5-coder`) by default; seamlessly switches to LLM when an API key is configured.

---

##  Environment Configuration

Set environment variables in your root `.env` or system environment:

| Variable | Default | Description |
| --- | --- | --- |
| `M5_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama model service URL |
| `M5_OLLAMA_MODEL` | `qwen2.5-coder:1.5b` | Local Ollama model name |
| `M5_QDRANT_HOST` | `localhost` | Qdrant vector database hostname |
| `M5_QDRANT_PORT` | `6333` | Qdrant vector database port |
| `M5_WORKSPACE_ROOT` | Current Directory | Root workspace path to index |
| `LLM_API_KEY` | *(empty)* | Optional LLM API KEY( OPENAI , CLAUDE etc.) (Unset falls back to Ollama) |
| `MODEL_NAME` | `model_name` | Model name when `LLM_API_KEY` is active |

---

##  Quick Start

### 1. Run Backend Stack with Docker Compose

```powershell
docker compose --env-file .env -f docker/docker-compose.m5.yml up -d
```

### 2. Run FastAPI Backend Locally

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 18000
```

### 3. Install Extension and make request calls

Install `M5-0.0.1.vsix` via VS Code and run 
