# Backend Agent: MarketPilot Build Playbook

You own `backend/`. The frontend builds against the contract in section 2; backend is the source of truth for it. Implement one phase at a time, meet its checks, commit, then continue.

**Core idea:** agent = LLM + harness. The LLM reasons; the harness owns state, context, verification, retries, budgets, checkpoints and the human gate.

---

## 1. What the backend is

FastAPI service at `/api/v1` plus a LangGraph pipeline that turns a campaign idea into an immutable campaign package.

```
POST /campaigns
  -> campaigns + workflow_runs rows
  -> background WorkflowRunLauncher
  -> brief -> research -> copywriter -> creative_director
     -> designer -> compliance -> reviewer
  -> compliance failure: rerun copywriter or designer
  -> score below threshold: rerun the weakest node
  -> human gate: approve (complete) or revise (new run + new version)
```

Every successful node writes an immutable `agent_outputs` row, a `workflow_checkpoints` row and an SSE handoff event. Redis carries the event stream; Postgres owns durable state.

**Stack:** Python 3.12, FastAPI, `uv`, LangGraph/LangChain, DeepSeek via `langchain-openai`, async SQLAlchemy + `asyncpg`, PostgreSQL + `pgvector`, Redis, Alembic, pytest, `ruff`, `mypy --strict`, httpx.

**Providers:**

- LLM: DeepSeek `deepseek-chat` through the OpenAI-compatible API.
- Images: `fake` (default), `hosted` generic HTTP, `huggingface`, or `cloudflare` Workers AI.
- Storage: `local` (default) or `cloudinary`.
- Embeddings: `fake` (default) or `huggingface`; policy vectors are 384-dimensional.
- Search: `fake` only. Video generation is not wired yet.

---

## 2. API contract (shared with the frontend agent)

Base path `/api/v1`. All bodies are JSON. Changes here must be mirrored in `frontend/agent.md`.

**Endpoints**

- `POST /campaigns` with `{ idea: string }` returns `{ campaign_id, run_id }`
- `GET /campaigns` returns `CampaignSummary[]`
- `GET /campaigns/{id}` returns one `CampaignSummary`
- `GET /campaigns/{id}/versions` returns `VersionSummary[]`, oldest first: `{ version, parent_version_id, score, created_at }`
- `GET /campaigns/{id}/versions/{n}` returns the full `CampaignPackage` for that version (no wrapper and no run metadata)
- `GET /campaigns/{id}/versions/{a}/diff/{b}` returns `{ from, to, changes: [{ path, before, after }] }`
- `POST /runs/{run_id}/approve` with `{ comment?: string }` returns `{ status: "completed", version }`
- `POST /runs/{run_id}/revise` with `{ comment: string, target_node?: string }` returns `{ run_id, version }`; `run_id` is the continuation run
- `GET /runs/{run_id}/stream` returns an SSE stream
- `GET /health` returns 200 at the root and under `/api/v1`

**Campaign summary shape** (items in `GET /campaigns` and the body of `GET /campaigns/{id}`)
`{ id, idea, status, latest_version: number | null, latest_score: number | null, active_run_id: string | null, created_at, updated_at }`

`status` is one of `draft`, `running`, `awaiting_approval`, `completed`, `failed`. `active_run_id` is the newest run that has not completed or failed.

**SSE events** (each has `id`, `event`, and JSON `data` with `run_id`, `timestamp`, `agent`)

- `agent_started`
- `agent_handoff` (from, to)
- `tool_called` (tool, duration_ms, status; status is `success`, `error`, or `denied`)
- `validation_failed` (reason)
- `retrying` (attempt, max_attempts)
- `awaiting_approval` (version)
- `completed` (version, score; score may be null)
- `error` (message, recoverable)

`agent` is one of the eight pipeline agents (`brief`, `research`, `copywriter`, `creative_director`, `designer`, `compliance`, `reviewer`, `supervisor`) or `human` for the approval gate and completion. Handoffs may target `human`.

**Stream behavior**

- The `id` of each SSE event is opaque and increasing; clients send the last one back as `Last-Event-ID`.
- The server closes the stream after a terminal event: `awaiting_approval`, `completed`, or `error` with `recoverable: false`.
- Clients must not reconnect after a terminal event. They reconnect only after an unexpected drop.

**Package shape (per version):**

- `brief`: `{ product, goal, audience, tone, channels, constraints }`
- `research`: `{ segments, pain_points, messaging_angles, sources }`, sources are `{ title, url }`
- `copy`: `{ variants }`, each variant is `{ channel, headline, description, cta }`
- `direction`: `{ style_guide, composition, image_prompts, video_prompts, negative_prompts }`
- `assets`: `{ assets }`, each asset is `{ uri, checksum, model, seed, prompt }`
- `compliance`: `{ items }`, each item is `{ check, passed, reason }`
- `score`: five dimensions (`brief_alignment`, `audience_fit`, `copy_quality`, `visual_quality`, `compliance_risk`), each `{ score, justification }`, plus `total`

**Errors:** `{ error: { code, message, details? } }` with the matching HTTP status.

---

## 3. Fresh setup (replicate the current state)

Prerequisites: Python 3.12, `uv`, Docker with Compose, and a DeepSeek API key for live runs.

From the repository root:

```bash
docker compose up -d postgres redis

cd backend
cp .env.example .env          # PowerShell: Copy-Item .env.example .env
# Set DEEPSEEK_API_KEY in .env. The defaults use fake images/search/embeddings.

uv sync                        # add --extra embeddings when EMBEDDER=huggingface
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Startup validates configuration, connects Redis, builds the tool registry and launcher, seeds the three sample policy documents, and idempotently creates the demo campaign `00000000-0000-4000-8000-000000000001`. It also resumes runs left `running` when `RESUME_ON_STARTUP=true`.

Verify:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health

curl -X POST http://localhost:8000/api/v1/campaigns \
  -H 'Content-Type: application/json' \
  -d '{"idea":"Create an advertising campaign for a fictional hair-care product targeting adults aged 25 to 40"}'
```

Use the returned `run_id` with `GET /api/v1/runs/{run_id}/stream`; the run stops at `awaiting_approval`.

Postgres-backed integration tests are skipped unless a test database is configured:

```bash
# from the repository root
docker compose exec postgres psql -U marketpilot -d marketpilot \
  -c "CREATE DATABASE marketpilot_test;"

cd backend
export TEST_DATABASE_URL=postgresql+asyncpg://marketpilot:marketpilot@localhost:5432/marketpilot_test
uv run pytest
```

Only `postgres` and `redis` are active in `docker-compose.yml`; the backend/frontend service blocks are commented out. The backend runs as a plain Python process.

---

## 4. Project structure

```
backend/
  app/
    main.py                 FastAPI app, lifespan, CORS, health, error handlers
    api/                    campaigns, versions, runs, stream, schemas, limits, capacity
    agents/
      prompts/              versioned .md prompt per LLM agent
      outputs/              frozen Pydantic output models
      base.py               prompt + context -> verified output
      brief.py research.py copywriter.py creative_director.py
      designer.py compliance.py reviewer.py
      supervisor.py supervisor_rules.py scoring.py
      designer_targets.py blocklist.py contracts.py
    graph/
      state.py              WorkflowState
      workflow.py           graph build, drive, resume, revision
      nodes.py              node wrappers: run, verify, persist, checkpoint, emit
      node_support.py routing.py versioning.py approvals.py diff.py
    harness/
      registry.py middleware.py guardrails.py retries.py
      checkpoints.py context.py verification.py validators.py
    tools/
      search_tools.py policy_tools.py
      image_tools.py image_models.py image_png.py
      image_providers/      fake selection, hosted, huggingface, cloudflare, storage
      asset_storage.py cloudinary_client.py cloudinary_storage.py
      export_tools.py export_models.py export_files.py
    llm/                    deepseek.py, embeddings.py
    runs/                   launcher.py, services.py, startup.py
    events/                 bus.py, emitter.py, envelope.py
    database/
      models/               one module per table
      repositories/         one module per aggregate
      session.py seed.py
    evaluation/             datasets.py evaluators.py golden.py runner.py
    core/                   config.py errors.py logging.py
  benchmarks/               image_models.py measure.py
  migrations/versions/      0001_initial_schema, 0002_policy_embedding_384
  tests/                    agents api database evaluation graph harness llm runs tools
  alembic.ini .env.example pyproject.toml README.md agent.md
```

Dependency direction: `api -> graph -> agents -> tools`; the harness wraps agents/tools. Agents never import `database` or call providers directly.

---

## 5. Configuration

`app/core/config.py` uses `pydantic-settings` and fails startup on missing required values. `.env` is gitignored; `.env.example` documents every setting and a test keeps the two in sync.

| Variable | Default | Notes |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | required | Provider key. |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible endpoint. |
| `DEEPSEEK_TIMEOUT_SECONDS` | `120` | Per-call deadline; 10s connect timeout. |
| `DEEPSEEK_MAX_RETRIES` | `2` | SDK transport retries for connect errors, 408/429/5xx. |
| `DATABASE_URL` | required | `postgresql+asyncpg://...`; append `?ssl=require` for external Postgres. |
| `REDIS_URL` | required | Event bus and rate-limit counters. |
| `EVENT_STREAM_MAXLEN` | `2000` | Max events retained per run stream. |
| `EVENT_STREAM_TTL_SECONDS` | `86400` | Stream expiry after a terminal event. |
| `RESUME_ON_STARTUP` | `true` | Claim and resume runs left `running`. |
| `IMAGE_PROVIDER` | `fake` | `fake`, `hosted`, `huggingface`, `cloudflare`. |
| `IMAGE_API_URL`, `IMAGE_API_KEY` | unset | Required for `hosted`. |
| `IMAGE_MODEL_ID` | `stabilityai/sdxl-turbo` | Hugging Face image model. |
| `IMAGE_TIMEOUT_SECONDS` | `45` | Total per-image deadline for every remote provider. |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | unset | Required for `cloudflare`. |
| `CLOUDFLARE_IMAGE_MODEL` | `@cf/black-forest-labs/flux-1-schnell` | Workers AI text-to-image model. |
| `CLOUDFLARE_EDIT_MODEL` | `@cf/runwayml/stable-diffusion-v1-5-img2img` | Workers AI img2img model. |
| `SEARCH_PROVIDER` | `fake` | Only `fake` is implemented. |
| `EMBEDDER` | `fake` | `fake` or `huggingface`. |
| `HF_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | 384-dimensional output. |
| `HUGGINGFACEHUB_API_TOKEN` | unset | Required for `EMBEDDER=huggingface` and image `huggingface`. |
| `ASSET_DIR` | `assets` | Local working copy for generated files. |
| `ASSET_STORAGE` | `local` | `local` or `cloudinary`. |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | unset | Required for `cloudinary`. |
| `CLOUDINARY_FOLDER`, `CLOUDINARY_TIMEOUT_SECONDS` | `marketpilot`, `30` | Upload folder and deadline. |
| `COST_CAP_PER_RUN` | `2.0` | Guardrail for projected/actual tool spend. |
| `MAX_IMAGE_CALLS_PER_RUN` | `8` | Shared cap across generate/edit/video calls. |
| `MAX_GENERATED_IMAGES_PER_RUN` | `2` | Prompts used per Designer run. |
| `MAX_SEARCH_CALLS_PER_RUN` | `20` | Research search cap. |
| `MAX_IMAGE_PROMPT_LENGTH` | `1000` | Validated prompt limit. |
| `RETRY_MAX_ATTEMPTS` | `3` | Verification retries before escalation. |
| `SCORE_THRESHOLD` | `70` | Below this the Reviewer loops to the weakest node. |
| `MAX_AUTO_LOOPS` | `2` | Shared compliance/score loop budget. |
| `MAX_IDEA_LENGTH`, `MAX_COMMENT_LENGTH` | `2000`, `2000` | Input limits. |
| `RATE_LIMIT_PER_MINUTE` | `20` | Writes per client IP; reads get 5x. |
| `MAX_CONCURRENT_RUNS` | `3` | New campaigns/revisions return `429 too_many_runs` above this. |
| `TRUST_PROXY` | `false` | Trust `X-Forwarded-For` only behind a known proxy. |
| `FRONTEND_ORIGIN` | `http://localhost:3000,https://marketpilot-demo-frontend.vercel.app` | Comma-separated CORS allowlist; no wildcards. |
| `LOG_LEVEL` | `INFO` | JSON logs with run/campaign/agent context. |

---

## 6. Data model

All schema changes go through Alembic; `create_all` is for tests only. Access tables through `app/database/repositories`, never raw SQL from agents/tools (the read-only policy lookup is the exception).

| Table | Key columns | Rules |
| --- | --- | --- |
| `campaigns` | `id`, `idea`, `status`, `created_at`, `updated_at` | Status: `draft/running/awaiting_approval/completed/failed`. |
| `workflow_runs` | `id`, `campaign_id`, `status`, `current_node`, `error` | Status: `pending/running/awaiting_approval/completed/failed`. |
| `workflow_checkpoints` | `id`, `run_id`, `step`, `node`, `state` | Unique `(run_id, step)`; append-only. |
| `agent_outputs` | `id`, `run_id`, `agent`, `output` | Append-only; one validated output per node. |
| `campaign_versions` | `id`, `campaign_id`, `version`, `parent_version_id`, `package`, `score` | Unique `(campaign_id, version)`; append-only; DB trigger rejects updates/deletes. |
| `assets` | `id`, `campaign_version_id`, `kind`, `uri`, `checksum`, `model`, `seed`, `prompt`, `media_type` | Binaries live on disk/object storage; DB stores metadata. |
| `compliance_reports` | `id`, `campaign_version_id`, `items`, `passed` | One per version. |
| `creative_scores` | `id`, `campaign_version_id`, `breakdown`, `total` | One per version. |
| `approvals` | `id`, `run_id`, `campaign_version_id`, `decision`, `comment`, `target_node` | Decision: `approve/revise`. |
| `tool_calls` | `id`, `run_id`, `agent`, `tool`, `args_hash`, `duration_ms`, `status`, `cost`, `error` | Append-only. |
| `policy_documents` | `id`, `title`, `source`, `content`, `metadata`, `embedding` | `embedding` is `vector(384)` on PostgreSQL. |

UUID primary keys. `created_at` on every row, `updated_at` on mutable rows. Version history is append-only: a revision adds `version + 1` with `parent_version_id`; prior rows are never updated. PostgreSQL triggers enforce the append-only rule for versions, agent outputs and tool calls.

**Agent output models** (`app/agents/outputs`, frozen, `extra="forbid"`):

| Model | Fields |
| --- | --- |
| `CampaignBrief` | product, goal, audience, tone, channels, constraints |
| `AudienceResearch` | segments `{name, description}`, pain_points, messaging_angles, sources `{title, url}` |
| `AdCopySet` | variants `{channel, headline, description, cta}` |
| `CreativeDirection` | image_prompts, video_prompts, style_guide, composition, negative_prompts |
| `AssetSet` | assets `{uri, checksum, model, seed, prompt}` |
| `ComplianceReport` | items `{check, passed, reason}` |
| `CreativeScore` | five dimensions `{score, justification}` + total |
| `RouteDecision` | next_node, reason, escalate (internal; not in the package) |

`WorkflowState` (`app/graph/state.py`) carries the idea, the seven package sections, `target_node`, `revision_feedback`, `versions`, `status`, `retry_counters` and `errors`.

**Scoring and routing:** each dimension is 0-10 and equally weighted (20%); `total = sum(score * 0.2) * 10` out of 100. `compliance_risk` is inverted (10 = lowest risk). Scores below `SCORE_THRESHOLD` rerun the weakest node. Compliance failures rerun copy first, otherwise visuals. Both loop types share `MAX_AUTO_LOOPS`; when exhausted the run stops at the human gate. Retry exhaustion also stops at the gate.

---

## 7. Agents, tools and guardrails

| Agent | Output | Tools |
| --- | --- | --- |
| Brief | `CampaignBrief` | read_state* |
| Research | `AudienceResearch` | `search_tools`, read_state* |
| Copywriter | `AdCopySet` | `policy_lookup`, read_state* |
| Creative Director | `CreativeDirection` | none |
| Designer | `AssetSet` | `generate_image`, `edit_image`, `generate_video` (unwired), read_state* |
| Compliance | `ComplianceReport` | `policy_lookup`, read_state* |
| Reviewer | `CreativeScore` | `policy_lookup`, read_state* |
| Supervisor | `RouteDecision` | deterministic; no LLM |

\* `read_state` is in the allowlist but not registered as a tool today. `export_package` exists under `app/tools/export_tools.py` but is granted to no agent and has no HTTP endpoint yet. Permissions are enforced by `harness/registry.py` with default deny; never by prompt wording.

Guardrails (`harness/guardrails.py`): image tools share `MAX_IMAGE_CALLS_PER_RUN`; search uses `MAX_SEARCH_CALLS_PER_RUN`; projected/actual spend is capped by `COST_CAP_PER_RUN`. Every call is recorded in `tool_calls` by the middleware. Inputs/outputs and retrieved text are validated at the boundary and fenced with `<untrusted source="...">` blocks.

A handoff is complete only when the validated output, the `agent_outputs` row, the checkpoint and the SSE event all exist.

---

## 8. Build phases

Build in this order; each phase is independently verifiable.

### Phase 1 — Bootstrap and infrastructure

- Create `backend/` with `uv init`; add FastAPI, uvicorn, pydantic, pydantic-settings, SQLAlchemy, asyncpg, psycopg, Alembic, redis, pgvector, LangGraph, LangChain, `langchain-openai`, python-dotenv.
- Add dev tools: pytest, pytest-asyncio, httpx, ruff, mypy, pip-audit, aiosqlite; optional `embeddings` extra: `langchain-huggingface`.
- Add `docker-compose.yml` (pgvector Postgres 17, Redis 7), `.env.example`, `.gitignore`, and the minimal `app/main.py` with `/health` and `/api/v1/health`.
- **Done when:** `docker compose up -d postgres redis` works, `uv run uvicorn app.main:app` starts, both health endpoints return 200, and `ruff`/`mypy` pass.

### Phase 2 — Core services and persistence

- `core/config.py`: validated settings, cached `get_settings()`, comma-separated CORS parsing. `core/logging.py`: JSON logs with run context. `core/errors.py`: typed errors with stable API codes.
- `database/models/`: all tables and enums from section 6. `database/session.py`: one shared async engine, per-request/run sessions. `database/repositories/`: one module per aggregate. `database/seed.py`: idempotent demo campaign + three policy documents.
- Alembic `0001_initial_schema` (tables, indexes, pgvector extension, append-only triggers) and `0002_policy_embedding_384`.
- **Done when:** `uv run alembic upgrade head` succeeds on a fresh database, repository tests pass, seed twice is a no-op, and updating a version/output/tool call is rejected.

### Phase 3 — Contracts, LLM and harness

- `graph/state.py`: `WorkflowState` plus `parse_agent_output`.
- `agents/outputs/`: frozen Pydantic models from section 6.
- `llm/deepseek.py`: one structured call per attempt, raw payload returned for verification, JSON-content fallback. `llm/embeddings.py`: fake and Hugging Face embedders.
- `harness/registry.py`, `guardrails.py`, `middleware.py`: allowlist, caps, audit rows.
- `harness/retries.py`, `verification.py`, `validators.py`: schema + semantic verification, exponential backoff with jitter, real error text fed into the next attempt.
- `harness/context.py`, `checkpoints.py`: per-agent token budgets, checkpoint after every node, resume by `run_id`, approval interrupt.
- **Done when:** failed-then-succeed and exhausted-then-escalate paths pass; a disallowed tool raises `GuardrailViolation`; a long fixture stays within budget; a simulated crash resumes at the right node.

### Phase 4 — Tools

- `search_tools.py` (fake provider, provenance), `policy_tools.py` (pgvector read-only lookup), `image_tools.py` and `image_providers/` (`fake`, `hosted`, `huggingface`, `cloudflare`), `asset_storage.py`/`cloudinary_storage.py` (local + Cloudinary), `export_tools.py` (filesystem export utility).
- Keep every tool typed and idempotent where possible; record model, seed, prompt and checksum for images.
- **Done when:** each tool has typed args/results and fake-based tests; image files record metadata; `huggingface` edit is rejected without a network call; Cloudflare handles both raw-byte and base64-JSON responses.

### Phase 5 — Agents, graph and approvals

- Implement the seven LLM agents in this order: Brief, Research, Copywriter, Creative Director, Designer, Compliance, Reviewer. Add the deterministic Supervisor after routing exists. Each LLM agent gets a versioned prompt in `agents/prompts/` and unit tests.
- `graph/nodes.py`: run through the harness, validate, persist, checkpoint, emit. `graph/workflow.py` and `routing.py`: linear edges, compliance loops, low-score loops, escalation, human gate. `runs/launcher.py`: background execution with a terminal error event; `runs/startup.py`: resume unfinished runs.
- `graph/versioning.py`: snapshot on approval with append-only version numbers. `graph/approvals.py`: record approve/revise, continue a revision in a new run.
- **Done when:** integration tests cover the happy path, compliance loop, low-score loop, retry escalation, crash/resume, approve and revise (new version linked to its parent).

### Phase 6 — API, SSE and security

- Implement every endpoint in section 2 with Pydantic schemas and the error envelope.
- `api/stream.py`: replay after `Last-Event-ID`, heartbeat comments every 5s, close on terminal events.
- `api/limits.py`: Redis fixed-window rate limits (writes `RATE_LIMIT_PER_MINUTE`, reads 5x). `api/capacity.py`: `MAX_CONCURRENT_RUNS`. CORS uses the `FRONTEND_ORIGIN` allowlist; wildcards are rejected. `TRUST_PROXY` gates `X-Forwarded-For`.
- **Done when:** httpx tests cover every router, SSE ordering and reconnect; API/schema tests pass; 429s are returned for limits/capacity; no secret or stack trace leaks.

### Phase 7 — Quality, evaluation and deployment

- Tests mirror `app/`: agents, outputs, harness, tools, graph, API, database, evaluation. Postgres tests use `TEST_DATABASE_URL` and the `postgres` marker. No live external API in tests.
- `app/evaluation/`: golden ideas, bad/clean claim fixtures, evaluators and the offline gate.
- `benchmarks/image_models.py`: `--dry-run` by default, live run only with `HUGGINGFACEHUB_API_TOKEN` and explicit confirmation.
- CI (`.github/workflows/backend.yml`): `uv sync --frozen`, ruff check/format, mypy, pytest (Postgres + Redis services), `alembic upgrade head`, `alembic check`, `pip-audit`, evaluation gate.
- Deployment: plain Python process on Render with `backend` as root; `uv sync --frozen --no-dev`, `alembic upgrade head`, then `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Health check `/health`.
- **Done when:** a fresh clone can create a campaign, stream it to `awaiting_approval`, approve it, and see the version through the API alone.

---

## 9. Verification commands

Run from `backend/`:

| Purpose | Command |
| --- | --- |
| Install | `uv sync` |
| Run API | `uv run uvicorn app.main:app --reload` |
| Migrate | `uv run alembic upgrade head` |
| Drift check | `uv run alembic check` |
| Tests | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Format check | `uv run ruff format --check .` |
| Types | `uv run mypy app` |
| Dependencies | `uv run pip-audit` |
| Offline evaluation | `uv run python -m app.evaluation.runner` |
| Image benchmark (offline) | `uv run python -m benchmarks.image_models --dry-run` |
| Seed manually | `uv run python -m app.database.seed` |

CI runs the same gates. Coverage is not enforced by a threshold today; keep new harness and graph branches covered anyway.

---

## 10. Working rules

1. One phase at a time. Meet its checks, commit, then start the next.
2. Read the existing code and tests before changing them; follow local patterns.
3. Smallest change that works. No drive-by refactors or dependencies without a reason.
4. Tests ship with behavior. Bug fixes get a regression test.
5. Run the real lint/type/test commands before claiming success.
6. Never commit `.env`, secrets, `node_modules`, `.venv`, build output or generated assets.
7. Contract changes are stop-and-confirm: update section 2 here and the matching section in `frontend/agent.md` in the same commit.
8. Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`). Backend and frontend changes in separate commits.
9. Keep new files under ~150 lines; split modules when they grow.
10. Ask when requirements are ambiguous or a step cannot be verified.

**Known current limits:** no export HTTP endpoint; `generate_video` is allowlisted but unwired; the `huggingface` image provider cannot edit; `search` and embeddings default to fakes; Docker Compose starts only Postgres and Redis.
