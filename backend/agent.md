# Backend Agent: MarketPilot

You are the **Backend Agent**. You own everything inside `backend/`: the multi-agent workflow, the harness, the database, the API, and the infrastructure to run them. You do NOT touch `frontend/`. The frontend agent builds against the API contract in section 2; if the contract must change, update section 2 in both `backend/agent.md` and `frontend/agent.md` in the same commit.

**Rule zero:** implement ONE step at a time. Finish its "Done when" criteria, commit, then move on. Never start step N+1 while step N is red.

**Core idea:** agent = LLM + harness. The LLM reasons; the harness provides memory and state persistence, context and token management, a verified execution loop, and guardrails with human approval.

---

## 1. Project Architecture

### 1.1 What the backend does

Accepts a campaign idea such as "Create an advertising campaign for a fictional hair-care product targeting adults aged 25 to 40" and runs it through a multi-agent pipeline that produces a campaign package: brief, audience research, copy, visual assets, compliance report, and creative score. A human approves or requests revisions. Every revision is a new version.

### 1.2 Workflow (LangGraph state machine)

1. User submits an idea.
2. Brief Agent structures it into a campaign brief.
3. Research Agent supplies audience and messaging research.
4. Copywriter Agent writes headlines, descriptions and CTAs.
5. Creative Director produces image/video generation instructions.
6. Designer Agent generates or edits visual assets.
7. Compliance Agent checks claims and policy restrictions.
8. Reviewer Agent scores the package.
9. Human approval gate: approve (done) or request revision (new version, routed to the targeted node).

The Supervisor routes between nodes. A failed node goes through the retry policy, then escalates to the human if retries are exhausted.

### 1.3 Stack

- Python 3.12, FastAPI, `uv` for environment and dependencies
- LangGraph and LangChain for orchestration (CrewAI only for comparison spikes)
- Primary LLM: DeepSeek through an OpenAI-compatible client (`langchain-openai`)
- Image generation: open-source model (FLUX.1 schnell or SDXL) behind an `ImageGenerator` interface
- Video generation: optional. Evaluate open-source models; if none is practical, keep a stub and skip video
- PostgreSQL with `pgvector`, SQLAlchemy (async) with `asyncpg`, Alembic migrations
- Redis for caching, pubsub and run locks
- Tests: `pytest`, `pytest-asyncio`, `httpx`

### 1.4 Backend layout

```
backend/
  app/
    main.py
    api/                routers: campaigns, runs, versions, approvals, stream
    agents/
      prompts/          one versioned .md prompt file per agent
      supervisor.py
      brief.py
      research.py
      copywriter.py
      creative_director.py
      designer.py
      compliance.py
      reviewer.py
    graph/
      workflow.py       graph definition and edges
      state.py          shared WorkflowState (pydantic)
      nodes.py          node wrappers that call the harness
    tools/
      image_tools.py
      search_tools.py
      policy_tools.py
      export_tools.py
    harness/
      registry.py       tool registry and per-agent permissions
      middleware.py     logging, timing, token accounting
      guardrails.py     policy enforcement and scopes
      retries.py        retry, backoff, fallback
      checkpoints.py    state persistence and human-in-the-loop
      context.py        token budget and context trimming
      verification.py   output validators and verify loop
    evaluation/
      datasets.py
      evaluators.py
      runner.py
    database/
      models.py
      session.py
      seed.py
      repositories/
    core/
      config.py
      logging.py
  migrations/           Alembic
  tests/
  pyproject.toml
  Dockerfile
```

Repo root (shared, owned by the backend agent for infra files): `docker-compose.yml`, `.env.example`, `README.md`.

Dependency direction: api calls graph, graph calls agents, agents call tools. The harness wraps agents and tools. Agents never import `database` or call external APIs directly; they go through tools and repositories.

---

## 2. API Contract (shared with the frontend agent)

Base path `/api/v1`. All bodies are JSON. Changes here must be mirrored in `frontend/agent.md`.

**Endpoints**

- `POST /campaigns` with `{ idea: string }` returns `{ campaign_id, run_id }`
- `GET /campaigns` returns a list of campaigns
- `GET /campaigns/{id}` returns the campaign with its latest version
- `GET /campaigns/{id}/versions` returns the version list
- `GET /campaigns/{id}/versions/{n}` returns the full package for a version
- `GET /campaigns/{id}/versions/{a}/diff/{b}` returns changed fields between two versions
- `POST /runs/{run_id}/approve` with `{ comment?: string }`
- `POST /runs/{run_id}/revise` with `{ comment: string, target_node?: string }`
- `GET /runs/{run_id}/stream` returns an SSE stream
- `GET /health` returns 200

**SSE events** (each has `id`, `event`, and JSON `data` with `run_id`, `timestamp`, `agent`)

- `agent_started`
- `agent_handoff` (from, to)
- `tool_called` (tool, duration_ms, status)
- `validation_failed` (reason)
- `retrying` (attempt, max_attempts)
- `awaiting_approval` (version)
- `completed` (version, score)
- `error` (message, recoverable)

Clients can reconnect with `Last-Event-ID` and resume.

**Package shape (per version):** `brief`, `research`, `copy` (variants per channel), `direction`, `assets` (uri, checksum, model, seed, prompt), `compliance` (items with pass/fail and reason), `score` (per-dimension scores, justifications, total).

**Errors:** `{ error: { code, message, details? } }` with correct HTTP status.

---

## 3. Coding Conventions

- Fully typed. `mypy --strict` clean on `app/`. Lint and format with `ruff`.
- Async by default for I/O. No blocking calls inside async functions.
- Pydantic v2 models at every boundary: API schemas, agent inputs and outputs, tool args, workflow state. No bare dicts crossing module boundaries.
- Settings only through `pydantic-settings` in `core/config.py`.
- JSON structured logging with `run_id`, `campaign_id`, `agent`, `step` on every line.
- Typed exceptions: `ToolError`, `ValidationFailure`, `GuardrailViolation`, `RetryExhausted`. Never swallow exceptions.
- Prompts live in `agents/prompts/*.md`, not inline strings.
- Docstrings on public functions explain why, not what.
- Conventional commits (`feat:`, `fix:`, `test:`, `chore:`). Never commit `.env`.

---

## 4. Agent Responsibilities

Each agent takes `(WorkflowState, allowed tools)` and returns a Pydantic output model. Agents do not mutate state directly; the node wrapper validates the output and merges it.

- **Supervisor** returns `RouteDecision`. Decides next node, handles revision routing, escalates on repeated failure. Must not generate creative content.
- **Brief** returns `CampaignBrief`: product, goal, audience, tone, channels, constraints. Must not invent medical or performance claims.
- **Research** returns `AudienceResearch`: segments, pain points, messaging angles. Must not cite sources it did not retrieve.
- **Copywriter** returns `AdCopySet`: headlines, descriptions and CTAs, several variants per channel. Must not make unsubstantiated claims.
- **Creative Director** returns `CreativeDirection`: image/video prompts, style guide, composition, negative prompts. Must not call image tools.
- **Designer** returns `AssetSet`: generates or edits visuals, records seed, prompt and model. Must not alter copy or direction.
- **Compliance** returns `ComplianceReport`: flags risky claims, restricted content and missing disclaimers with a pass/fail and reason per item. Flags only; it does not rewrite copy.
- **Reviewer** returns `CreativeScore`: scores the package and recommends revisions. Must not approve on behalf of the human.

**Scoring rubric** (0 to 10 each, one-line justification, weighted total out of 100): brief alignment 20%, audience fit 20%, copy quality 20%, visual quality and brand consistency 20%, compliance risk (inverted) 20%. Below the threshold (default 70) the package routes back to the weakest node, maximum 2 automatic loops, then escalates to the human.

**Handoff contract:** a handoff means a validated output written to `WorkflowState`, an SSE event emitted, and a checkpoint persisted. A handoff missing any of the three is a bug.

---

## 5. Tool Permissions

Declared as a per-agent allowlist in `harness/registry.py`. Default deny.

- `search_tools`: Research only
- `policy_lookup` (pgvector, read-only): Copywriter, Compliance, Reviewer
- `generate_image`, `edit_image`, `generate_video` (optional): Designer only
- `read_state`: all agents
- `export_package`: no agent; the API invokes it only after a recorded human approval

Rules:

- Tools validate arguments with Pydantic and are idempotent where possible.
- Every tool call is logged: agent, tool, args hash, duration, cost, outcome.
- Side-effecting tools have per-run call caps set in config.
- Human approval is required before final export and before any run exceeds the cost cap.

---

## 6. Database Rules

- All schema changes go through Alembic migrations. No manual DDL; `create_all` only in tests.
- Minimum tables: `campaigns`, `workflow_runs`, `workflow_checkpoints`, `agent_outputs`, `campaign_versions`, `assets`, `compliance_reports`, `creative_scores`, `approvals`, `tool_calls`, `policy_documents` (with a vector column).
- UUID primary keys. `created_at` on every row, `updated_at` on mutable rows.
- Version history is append-only: a revision creates a new `campaign_versions` row with `parent_version_id`. Never update a prior version.
- Agent outputs and tool calls are immutable once written.
- Binaries (images, video) live on disk or object storage. The database stores URI, checksum and generation metadata.
- Access only through repository functions. No raw SQL in agents or tools, except read-only parameterized queries in policy lookup.
- One async session per request or run, closed by a context manager. No global sessions.
- Index every foreign key and `(campaign_id, version)`.
- `seed.py` loads sample policy documents and a demo campaign, and is idempotent.

---

## 7. Testing Requirements

- **Unit:** every agent, tool, validator, retry policy and guardrail. LLM and image calls use deterministic fakes.
- **Harness (mandatory):** retry then succeed, retry exhausted then escalate, guardrail blocks a disallowed tool, context trimming stays under budget, checkpoint resume reproduces state.
- **Integration:** full graph run with fake LLM and fake image tool against real Postgres. Cover happy path, compliance-fail revision loop, human rejection creating a new version, and crash then resume.
- **API:** `httpx.AsyncClient` tests for every router, including SSE event ordering and `Last-Event-ID` resume.
- **Contract:** a test that checks responses against the section 2 shapes so the frontend never breaks silently.
- **Evaluation:** golden briefs in `evaluation/`; evaluators check schema validity, compliance recall on seeded bad claims, and score stability. Run with `uv run python -m app.evaluation.runner`.
- Coverage: at least 85% on `harness/` and `graph/`, at least 75% overall.
- No test calls a live external API unless marked `@pytest.mark.live` (excluded from CI).

---

## 8. Security Restrictions

- Secrets only from environment. `.env.example` holds placeholders only.
- Treat all retrieved, web and user text as untrusted data. Delimit it in prompts. Tool permissions are enforced in code (registry), never by prompt wording.
- Validate and size-limit all input. Reject on schema failure.
- Validate outputs before persistence: sanitize copy, verify image MIME, size and checksum.
- Compliance and Designer refuse or flag disallowed content: unapproved medical claims, guaranteed results, targeting minors, real people's likenesses, copyrighted characters or brands.
- Rate limit endpoints and cap concurrent runs per user.
- CORS limited to the known frontend origin; no wildcard in production.
- No `eval`, `exec` or shell execution from agents. Agents write files only inside the asset directory.
- Pin dependencies (`uv.lock`) and run `pip-audit` in CI.
- Never log API keys or full prompts containing personal data; log IDs and hashes.
- Dockerfile: non-root user, minimal base image, no secrets baked in.

---

## 9. Infrastructure Workflow (step by step)

Work strictly in order. Each step: goal, tasks, done when.

### Step 0: Repo and tooling bootstrap

- Create the layout from section 1.4. In `backend/` run `uv init`, then:
  ```
  uv add fastapi uvicorn
  uv add langgraph langchain langchain-openai
  uv add pydantic pydantic-settings
  uv add sqlalchemy asyncpg psycopg alembic
  uv add redis pgvector python-dotenv
  uv add --dev pytest pytest-asyncio httpx ruff mypy pip-audit
  ```
- `docker-compose.yml` with `postgres` (pgvector image), `redis`, `backend`, and a `frontend` service placeholder the frontend agent will fill in.
- `.env.example`: `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DATABASE_URL`, `REDIS_URL`, `IMAGE_PROVIDER`, `COST_CAP_PER_RUN`, `FRONTEND_ORIGIN`.
- **Done when:** `docker compose up` starts the services, `GET /health` returns 200, `pytest` runs one placeholder test, `ruff` and `mypy` pass.

### Step 1: Core config and logging

- `core/config.py` and `core/logging.py` with `run_id` context variables.
- **Done when:** missing required variables fail fast with a clear error; a test asserts `run_id` appears in logs.

### Step 2: Database layer

- Models (section 6), async session, Alembic initial migration, repositories, `seed.py`.
- **Done when:** `alembic upgrade head` works on a fresh DB; repository tests pass; seed is idempotent; a test confirms versions cannot be mutated.

### Step 3: Workflow state and schemas

- `WorkflowState` and the output model for every agent.
- **Done when:** state round-trips through serialization; invalid output raises `ValidationFailure`.

### Step 4: LLM client abstraction

- `LLMClient` wrapping DeepSeek with structured output (schema to Pydantic), timeout and token usage. Add a fake client.
- **Done when:** a structured call returns a validated model; malformed JSON raises a controlled error; token usage is captured.

### Step 5: Harness: registry, guardrails, middleware

- Allowlist from section 5, call caps, and middleware that records every call to `tool_calls`.
- **Done when:** a disallowed tool call raises `GuardrailViolation`; every call writes a DB row; tests cover allow, deny and cap.

### Step 6: Harness: retries and verification loop

- Exponential backoff with jitter, retry only retryable errors, optional fallback provider. The verifier runs schema and semantic checks after each output and feeds the real error message back into the retry prompt.
- **Done when:** fail then succeed and fail N times then escalate are both tested.

### Step 7: Harness: context, memory, checkpoints

- Token budgeting that gives each agent only the state it needs. Checkpoints after every node, resume by `run_id`, interrupt and resume for human approval.
- **Done when:** a simulated crash resumes at the right node; context stays under budget on a long fixture.

### Step 8: Tools

- Search with provenance, pgvector policy lookup, `ImageGenerator` interface with a local open-source implementation and a fake, optional video stub, export.
- **Done when:** each tool has typed args and results, fake-based tests, and image outputs record model, seed, prompt and checksum.

### Step 9: Agents, one at a time

- Order: Brief, Research, Copywriter, Creative Director, Designer, Compliance, Reviewer, Supervisor. Each gets a prompt file, unit tests and an evaluation case.
- **Done when (per agent):** valid output on fixtures, respects permissions, has a failure-path test.

### Step 10: LangGraph workflow

- Nodes wrap agents through the harness: guardrails, run, verify, checkpoint, emit event. Conditional edges for compliance failure, low score (max 2 loops) and the human gate.
- **Done when:** integration tests pass for happy path, compliance loop, low-score loop and resume after crash.

### Step 11: Versioning and approvals

- Each package becomes a `campaign_versions` row. Approvals record approve or revise, comment and target node.
- **Done when:** a rejection with a comment creates version N+1 linked to N; the diff endpoint works; export requires approval.

### Step 12: API and SSE

- Implement every endpoint and event in section 2.
- **Done when:** httpx tests assert event order for a full run, reconnect with `Last-Event-ID` resumes, and the contract test passes.

### Step 13: Evaluation harness

- Golden dataset, evaluators and runner.
- **Done when:** the runner works offline with fakes, prints pass rates, and a regression fails CI.

### Step 14: Image and video model exploration

- Benchmark 2 to 3 open-source image models on the same 5 briefs (quality, latency, VRAM, licence). Evaluate one open-source video model; if impractical, document it and keep the stub.
- **Done when:** `docs/model-decision.md` records results and the chosen default.

### Step 15: Hardening, CI and deployment

- Review section 8, add rate limiting, harden the Dockerfile, set up CI (ruff, mypy, pytest, pip-audit, migration check), and write the backend README section with setup and run instructions.
- **Done when:** a fresh clone runs `docker compose up` and the demo campaign completes via the API alone.

---

## 10. Definition of Done

A step is done only when all of these hold:

1. Code follows section 3 and the dependency direction in section 1.4.
2. Tests pass, including relevant integration tests, and coverage gates are met.
3. `ruff` and `mypy --strict` report zero errors.
4. No security restriction in section 8 is violated; no secrets in code or logs.
5. Database changes are migrations that apply cleanly to a fresh database.
6. Every agent and tool action is logged; handoffs emit SSE events and checkpoints.
7. Failure paths exist and are tested (retry, escalation, guardrail denial).
8. The API contract in section 2 is unchanged, or updated in both agent files.
9. Docs updated, conventional commit made, CI green.
10. The step's own "Done when" criteria are demonstrably met.
