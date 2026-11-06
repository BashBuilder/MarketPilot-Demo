# MarketPilot

MarketPilot is an autonomous advertising creative pipeline. A campaign idea becomes a structured brief, audience research, copy, visual direction and assets, a compliance report, and a creative score, then waits for human approval. Every revision creates a new, append-only version that can be compared with the version before it.

> Current status: the API, database, agents, harness, and frontend are implemented. The graph launcher, live LLM client, and offline evaluation runner are not wired yet; see [Limitations](#limitations).

## Architecture

The pipeline is a state machine with eight agents:

- **Brief** turns the raw idea into product, goal, audience, tone, channels, and constraints.
- **Research** produces audience segments, pain points, messaging angles, and source provenance.
- **Copywriter** writes several headline, description, and CTA variants per channel.
- **Creative Director** defines the style guide, composition, image prompts, video prompts, and negative prompts.
- **Designer** generates or edits visual assets and records the model, seed, prompt, and checksum for each one.
- **Compliance** checks claims and policy restrictions and returns pass/fail plus a reason per item.
- **Reviewer** scores brief alignment, audience fit, copy quality, visual quality, and compliance risk, then computes a weighted total.
- **Supervisor** chooses the next agent and routes revisions; it does not write creative content.

The **harness** wraps the agents and tools. It provides the per-agent tool allowlist and guardrails, structured logging and timing middleware, retries with backoff, token/context budgeting, checkpoint persistence, and output verification. The harness is the part that makes an agent a bounded, observable, recoverable worker.

The **human approval gate** comes after review. A run stops at `awaiting_approval`; a human can approve it and complete the run, or request a revision with a comment and an optional target agent. The revision starts a continuation run and produces the next package version.

**Version history** is append-only. A version references its parent through `parent_version_id`, prior versions are never mutated, and the API exposes version listing, a full package per version, and a diff between any two versions.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

On PowerShell, use `Copy-Item .env.example .env` instead of `cp`.

Open `http://localhost:3000` and submit the demo idea:

> Create an advertising campaign for a fictional hair-care product targeting adults aged 25 to 40.

The stack runs PostgreSQL with pgvector, Redis, the FastAPI backend on port 8000, and the Next.js frontend on port 3000. Compose waits for the database, Redis, and backend health checks before starting the frontend.

In the current checkout, submitting an idea creates a campaign and a run, but the API's launcher only records the run id. The graph does not execute until the launcher is wired; see [Limitations](#limitations).

## Modes

`.env.example` sets `APP_MODE=fake`. In local mode, Compose also defaults `IMAGE_PROVIDER`, `SEARCH_PROVIDER`, and `EMBEDDER` to `fake` and supplies a placeholder `DEEPSEEK_API_KEY`, so no real provider keys are needed. Note that the backend currently reads the provider variables, not `APP_MODE` itself.

For real providers, set `DEEPSEEK_API_KEY` and `DEEPSEEK_BASE_URL`, then choose an image provider:

- `IMAGE_PROVIDER=hosted` requires `IMAGE_API_URL` and `IMAGE_API_KEY`.
- `IMAGE_PROVIDER=local` requires `uv sync --extra images` and runs a diffusers pipeline locally.

See [docs/model-decision.md](docs/model-decision.md) for the image and video decision record. That document is pending in this checkout; the current code state is reflected below.

Real mode still needs the live LLM client to be wired; see [Limitations](#limitations).

## Tests

Backend, from `backend/`:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

Frontend, from `frontend/`:

```bash
pnpm install
pnpm test
pnpm lint
pnpm typecheck
pnpm build
pnpm e2e:mock
```

`pnpm e2e:mock` runs the Playwright happy path, accessibility checks, responsive checks, and security-header checks against the in-app MSW mock API.

## Evaluation runner

The intended command is:

```bash
cd backend
uv run python -m app.evaluation.runner
```

The pure evaluators live in `app/evaluation/evaluators.py`, but `app/evaluation/runner.py` is not present in this checkout, so the command currently exits with `No module named app.evaluation.runner`. The evaluation dataset and metrics cover schema validity, compliance recall on seeded bad claims, automatic-loop behavior, and score stability. They measure harness behavior, not generated content quality.

## Live checks

Start the backend first, then run the real-backend Playwright project from `frontend/`:

```bash
E2E_API_URL=http://localhost:8000/api/v1 pnpm e2e:real
```

The image benchmark supports an offline dry run and a live Hugging Face run:

```bash
cd backend
uv run python -m benchmarks.image_models --dry-run
HUGGINGFACEHUB_API_TOKEN=... uv run python -m benchmarks.image_models --model stabilityai/sdxl-turbo --yes
```

The live run calls Hugging Face Inference Providers and asks for confirmation unless `--yes` is passed. No live `@pytest.mark.live` tests are present in this checkout.

## Tool permissions

Permissions are declared in `backend/app/harness/registry.py` and enforced in code, not in prompts. Default deny.

| Tool | Allowed agents | Notes |
| --- | --- | --- |
| `search_tools` | Research | Returns results with source provenance. |
| `policy_lookup` | Copywriter, Compliance, Reviewer | Read-only pgvector lookup. |
| `generate_image` | Designer | Writes an image and records model, seed, prompt, checksum. |
| `edit_image` | Designer | Edits an existing image with a recorded instruction. |
| `generate_video` | Designer | Permission entry only; no video generator is registered. |
| `read_state` | All agents except Creative Director | Creative Director has no tools. |
| `export_package` | No agent | The API invokes it only after a recorded human approval. |

## API contract

The base path is `/api/v1`. All bodies are JSON. The full contract is in [backend/agent.md, section 2](backend/agent.md#2-api-contract-shared-with-the-frontend-agent).

Main endpoints:

- `POST /campaigns` creates a campaign and its first run.
- `GET /campaigns` and `GET /campaigns/{id}` return campaign summaries.
- `GET /campaigns/{id}/versions` returns version summaries, oldest first.
- `GET /campaigns/{id}/versions/{n}` returns the full package for one version.
- `GET /campaigns/{id}/versions/{a}/diff/{b}` returns changed paths with before/after values.
- `POST /runs/{run_id}/approve` completes a run at the human gate.
- `POST /runs/{run_id}/revise` starts a continuation run and creates a new version.
- `GET /runs/{run_id}/stream` is the SSE stream.
- `GET /health` is available at the root and under `/api/v1`.

SSE events are `agent_started`, `agent_handoff`, `tool_called`, `validation_failed`, `retrying`, `awaiting_approval`, `completed`, and `error`. Each event carries `run_id`, `timestamp`, and `agent`. A package contains `brief`, `research`, `copy`, `direction`, `assets`, `compliance`, and `score`. Errors use `{ "error": { "code", "message", "details?" } }`.

## Limitations

- **No authentication.** This is a demo; do not expose it to an untrusted network.
- **Run execution is not wired yet.** Runs are intended to execute inside the API process, but `main.py` currently installs `RecordingRunLauncher`, which only records run ids. The live LLM client is also a placeholder (`_UnavailableLLM`), so supplying `DEEPSEEK_API_KEY` does not make the agent graph run.
- **`APP_MODE` is not read by the backend.** The no-key local setup comes from Compose's fake provider defaults and placeholder key, not from `APP_MODE`.
- **The offline evaluation checks the harness, not model quality.** The evaluators test schema validity, compliance recall, loop behavior, and score stability.
- **The evaluation runner is pending.** `app/evaluation/runner.py` is absent in this checkout.
- **Video is not enabled.** The Creative Director produces video prompts and the registry grants a `generate_video` permission, but no video generator or executor is implemented.
- **The model decision record is pending.** `docs/model-decision.md` is referenced but not present in this checkout.
