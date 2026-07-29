# M5

M5 is a customer-controlled code-intelligence service for answering questions about approved internal repositories with evidence from a known repository snapshot. It is currently a developer-demo foundation, not a production deployment.

## Milestone 1 configuration

All application settings are supplied through environment variables. Do not commit credentials, repository paths, or customer model artifacts.

| Variable | Default | Purpose |
| --- | --- | --- |
| `M5_ALLOWED_ORIGINS` | empty | Comma-separated, explicit browser origins. Wildcards are rejected. |
| `M5_OLLAMA_BASE_URL` | `http://localhost:11434` | Approved local model-service URL. |
| `M5_OLLAMA_MODEL` | `qwen2.5-coder:1.5b` | Approved local model name. |
| `M5_REQUEST_TIMEOUT_SECONDS` | `30` | Positive timeout for model calls. |
| `M5_QDRANT_HOST` | `localhost` | Qdrant hostname within the customer environment. |
| `M5_QDRANT_PORT` | `6333` | Qdrant port. |
| `M5_WORKSPACE_ROOT` | current directory | Repository workspace selected by the deployment owner. |
| `NVIDIA_API_KEY` | empty | Optional NVIDIA NIM credential. Keep it in a secret store or ignored `.env` file; an unset value uses Ollama. |
| `NVIDIA_MODEL` | `nvidia/nemotron-3-ultra-550b-a55b` | NVIDIA model selected when `NVIDIA_API_KEY` is set. |

The API no longer indexes a workspace when it starts. Indexing must be requested explicitly, and it always uses `M5_WORKSPACE_ROOT`; clients cannot submit an arbitrary server path.

For local development from `backend/`, run `uvicorn app.main:app --host 127.0.0.1 --port 8000`. This is a trusted local/demo configuration: it has no authentication, repository authorization, administrative console, or audit records. Those controls must be restored before sharing the service with users.

## Local demo setup

For a repeatable local demo, create a root-level `.env` file (it is ignored by Git):

```dotenv
TARGET_CODEBASE=D:/path/to/approved/repository
M5_OLLAMA_MODEL=qwen2.5-coder:1.5b
```

Start the local stack from the project root:

```powershell
docker compose --env-file .env -f docker\docker-compose.m5.yml up -d
```

Index the mounted repository by calling `POST /api/v1/index`. The API always uses `M5_WORKSPACE_ROOT`; callers cannot submit an arbitrary server path. Get the branch and commit values from the mounted repository with `git -C D:\path\to\approved\repository branch --show-current` and `git -C D:\path\to\approved\repository rev-parse HEAD`.

## Run the current automated checks

From the `backend` folder, run the following commands. Replace the Python path if it is installed elsewhere on your computer.

```powershell
& "C:\Users\Aman\AppData\Local\Programs\Python\Python314\python.exe" -m compileall -q app
& "C:\Users\Aman\AppData\Local\Programs\Python\Python314\python.exe" -m pytest tests\test_config.py tests\test_api_endpoints.py tests\test_chunk_identity.py tests\test_nvidia_llm_client.py
```

These checks do not start Ollama, Qdrant, Docker, or indexing; they use safe mock replacements for external services.

## Repository indexing

Every index request identifies the repository, branch, and commit SHA. M5 stores those details with each code chunk, together with the file path and line numbers. This is the foundation for answer citations.

## Evidence-first answers

To ask a question, the API now requires `repository_id` and `commit_sha`. M5 applies both values as Qdrant filters, so it searches only the requested repository snapshot. Each answer contains `grounded`, `confidence`, and `citations`; each citation identifies the repository, commit, file path, line range, stable chunk ID, and retrieval score.

If no matching evidence is retrieved, M5 returns a clear refusal with `grounded: false` and no citations. The model is instructed to answer only from the supplied context and to ignore instructions hidden inside repository content.

For the VS Code extension, set `m5.repositoryId` and `m5.commitSha` in VS Code Settings. The panel displays source details below every grounded answer. Streaming is deliberately disabled for cited answers in this version because M5 must return the final answer together with its complete citation list.
