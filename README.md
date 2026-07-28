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
| `M5_WEBHOOK_SECRET` | unset | Secret used to verify code-push notifications. Required before enabling webhooks. |
| `M5_AUTH_SECRET` | unset | Secret used to sign local login tokens. Required before protected API use. |
| `M5_AUTH_TOKEN_MINUTES` | `60` | How long a local login token remains valid. |
| `M5_DATABASE_PATH` | `m5.db` | Path for local users, access grants, and audit events. |
| `M5_BOOTSTRAP_ADMIN_USERNAME` | unset | One-time local admin username. |
| `M5_BOOTSTRAP_ADMIN_PASSWORD` | unset | One-time local admin password; use a secret store in real deployments. |

The API no longer indexes a workspace when it starts. Indexing must be requested explicitly, and it always uses `M5_WORKSPACE_ROOT`; clients cannot submit an arbitrary server path.

For local development from `backend/`, run `uvicorn app.main:app --host 127.0.0.1 --port 8000`. Production setup, authentication, repository snapshots, citations, and audit logging remain later milestones.

## Run the current automated checks

From the `backend` folder, run the following commands. Replace the Python path if it is installed elsewhere on your computer.

```powershell
& "C:\Users\Aman\AppData\Local\Programs\Python\Python314\python.exe" -m compileall -q app
& "C:\Users\Aman\AppData\Local\Programs\Python\Python314\python.exe" -m pytest tests\test_config.py tests\test_api_endpoints.py tests\test_chunk_identity.py tests\test_webhooks.py tests\test_security.py
```

Expected result: eleven tests pass. These checks do not start Ollama, Qdrant, Docker, or indexing; they use safe mock replacements for external services.

## Repository indexing and automatic updates

Every index request must identify the repository, branch, and commit SHA. M5 stores those details with each code chunk, together with the file path and line numbers. This is the foundation for future answer citations.

When a developer pushes code, your Git provider will eventually send M5 a signed `POST /api/v1/webhooks/push` request. M5 verifies the `X-M5-Signature` header using `M5_WEBHOOK_SECRET` before it considers the event. It then re-indexes only reported changed files and removes chunks for reported deleted files; it never accepts a server folder path from the webhook.

Do not expose the webhook endpoint to the public internet for a customer pilot. Put it behind the customer internal network or reverse proxy, use TLS, store `M5_WEBHOOK_SECRET` in an approved secret store, and configure a separate secret for each environment. GitHub, GitLab, and Bitbucket payload adapters will be configured in a later milestone.

## Evidence-first answers

To ask a question, the API now requires `repository_id` and `commit_sha`. M5 applies both values as Qdrant filters, so it searches only the requested repository snapshot. Each answer contains `grounded`, `confidence`, and `citations`; each citation identifies the repository, commit, file path, line range, stable chunk ID, and retrieval score.

If no matching evidence is retrieved, M5 returns a clear refusal with `grounded: false` and no citations. The model is instructed to answer only from the supplied context and to ignore instructions hidden inside repository content.

For the VS Code extension, set `m5.repositoryId`, `m5.commitSha`, and the temporary `m5.accessToken` in VS Code Settings. Use personal/user settings for the token; never commit it in workspace settings. The panel displays source details below every grounded answer. Streaming is deliberately disabled for cited answers in this version because M5 must return the final answer together with its complete citation list.

## Local login, roles, and audit records

M5 now requires a login token before it searches a repository or starts indexing. Set these values before starting the backend. Use long random values; do not commit them to Git.

```powershell
$env:M5_AUTH_SECRET = "replace-with-a-long-random-secret"
$env:M5_DATABASE_PATH = "$PWD\m5.db"
$env:M5_BOOTSTRAP_ADMIN_USERNAME = "m5-admin"
$env:M5_BOOTSTRAP_ADMIN_PASSWORD = "replace-with-a-strong-password"
```

Start M5 once. It creates the bootstrap admin only if that username does not already exist. Then log in:

```powershell
$body = @{ username = "m5-admin"; password = "replace-with-a-strong-password" } | ConvertTo-Json
$login = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/auth/login" -ContentType "application/json" -Body $body
$token = $login.access_token
```

Use the token in requests with the header `Authorization: Bearer <token>`. The roles are `admin`, `repository_manager`, `developer`, and `auditor`. Developers need an explicit repository-access grant; admins and repository managers can access approved repositories for administration and indexing.

Audit records capture actions such as login, indexing, denied repository access, successful questions, and errors. They store actor, time, action, repository, commit, outcome, correlation ID, and small safe details such as citation count. They do not store passwords, tokens, full source code, or the raw user question by default.

Important: SQLite is used only for the developer demo. Before a paid pilot, move this data to PostgreSQL on a persistent customer-managed volume, use OIDC instead of local passwords when available, and send audit records to the customer's SIEM.
