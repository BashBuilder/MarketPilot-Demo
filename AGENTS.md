# AGENTS.md

Root instructions for AI coding agents working in this monorepo. Read this first, then read the guide for the area you are working in.

## 1. Project Overview

MarketPilot is an autonomous advertising creative pipeline. A user submits a campaign idea; a multi-agent backend produces a campaign package (brief, research, copy, visuals, compliance report, creative score); a human approves or requests revisions; every revision becomes a new version. The frontend streams agent activity live and handles review and approval.

Core idea: agent = LLM + harness. The harness provides state persistence, context management, a verified execution loop with retries, and guardrails with human approval.

## 2. Repo Layout

```
marketpilot/
  AGENTS.md              this file: rules shared by everything
  backend/
    agent.md             backend guide (owns the API contract and infra workflow)
    app/ migrations/ tests/ pyproject.toml Dockerfile
  frontend/
    agent.md             frontend guide (builds against the API contract)
    src/ e2e/ package.json Dockerfile
  docker-compose.yml     local stack: postgres (pgvector), redis, backend, frontend
  .env.example           placeholders only
  README.md
```

## 3. Which Guide to Follow

Work in one area at a time and load only that area's guide.

- Task touches `backend/`: follow `backend/agent.md`. Do not edit `frontend/`.
- Task touches `frontend/`: follow `frontend/agent.md`. Do not edit `backend/`.
- Task touches both (for example a new endpoint plus its UI): split it into a backend task first, then a frontend task. Finish and commit the backend half before starting the frontend half.
- Task touches root files (`docker-compose.yml`, `.env.example`, `README.md`, this file): the backend guide owns infra files; keep changes minimal and tell the user what you changed.

Working directory matters. If opencode was started inside `backend/` or `frontend/`, that area's guide is `./agent.md` and this file is `../AGENTS.md`. Root-level commands (`docker compose`, editing `.env.example`) need `cd ..` first. Stay inside your starting area unless the task says otherwise.

If a guide and this file disagree, the area guide wins for that area. If two guides disagree with each other, stop and ask.

## 4. Shared Contract

The API contract (endpoints, SSE events, package shape, error format) lives in section 2 of both area guides and must stay identical in both.

- Backend is the source of truth. Frontend consumes it.
- Never change the contract in one file only. Update both guides in the same commit as the code change.
- Contract changes are a stop-and-confirm moment: describe the change to the user before making it.

## 5. Stack Summary

- Backend: Python 3.12, FastAPI, `uv`, LangGraph/LangChain, DeepSeek (primary LLM), open-source image model behind an interface, PostgreSQL with pgvector, Redis, Alembic, pytest.
- Frontend: Next.js (App Router), TypeScript strict, Tailwind, shadcn/ui, Recharts, Zod, SSE, `pnpm`, Vitest, Playwright, MSW.
- Infra: Docker Compose for local development.

Use `uv` for Python and `pnpm` for JavaScript. Do not introduce `pip`, `poetry`, `npm` or `yarn` files.

## 6. Commands

Run these from the stated directory. If a command does not exist yet, the step that creates it is still pending; do not invent a replacement.

Root:

- `docker compose up` starts the full local stack
- `docker compose up postgres redis` starts only the data services

Backend (`backend/`):

- `uv sync` installs dependencies
- `uv run uvicorn app.main:app --reload` runs the API
- `uv run pytest` runs tests
- `uv run ruff check . && uv run ruff format --check .` lint and format check
- `uv run mypy app` type check
- `uv run alembic upgrade head` applies migrations
- `uv run python -m app.evaluation.runner` runs the evaluation suite

Frontend (`frontend/`):

- `pnpm install` installs dependencies
- `pnpm dev` runs the app, `pnpm dev:mock` runs it against the mock API
- `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm test`, `pnpm build`
- `pnpm exec playwright test` runs end-to-end tests

## 7. Working Rules

1. **One step at a time.** The area guides define numbered steps. Implement one, meet its "Done when" criteria, commit, then move on. Never start the next step while the current one is failing.
2. **Read before you write.** Inspect existing code, tests and the relevant guide section before changing anything. Follow existing patterns over personal preference.
3. **Smallest change that works.** No drive-by refactors, no renaming unrelated code, no new dependencies without saying why.
4. **Tests come with the code.** New behavior needs tests in the same change. A bug fix needs a test that fails without the fix.
5. **Verify before claiming done.** Run the relevant lint, type check and tests and report the real results. Do not say something passes unless you ran it.
6. **Ask when blocked.** If requirements are ambiguous, the contract needs to change, or a step's criteria cannot be met, stop and ask rather than guessing.
7. **Keep the user informed.** After each step, summarize what changed, what was verified, and what is next.

## 8. Git Conventions

- Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`.
- One focused commit per logical change. Backend and frontend changes go in separate commits.
- Never commit `.env`, secrets, generated assets, `node_modules`, `.venv` or build output.
- Do not rewrite history, force push, or change branches the user did not ask you to touch.
- Do not commit or push unless the user asked you to or the step's workflow says to.

## 9. Security Rules (apply everywhere)

- No secrets in code, logs, commits or frontend bundles. Configuration comes from environment variables; `.env.example` holds placeholders only.
- Treat all user input, retrieved web content and model output as untrusted. Validate at every boundary (Pydantic on the backend, Zod on the frontend).
- Permissions are enforced in code, never by prompt wording alone.
- Never execute shell commands, `eval` or arbitrary code derived from model output.
- Do not run destructive commands (dropping databases, deleting volumes, `rm -rf` outside build output) without explicit user confirmation.
- Do not call paid or live external APIs in tests. Use fakes; live tests must be explicitly marked and excluded from CI.

## 10. Code Quality Baseline

- Backend: fully typed, `mypy --strict` clean, `ruff` clean, async by default for I/O, Pydantic models at boundaries.
- Frontend: TypeScript `strict`, no `any`, Zod-validated responses, loading, empty and error states on every view, accessible by default.
- Clear names over clever code. Comments explain why, not what.
- Handle errors explicitly. Never swallow exceptions.

## 11. Definition of Done (any task)

A task is done only when all of these hold:

1. The change follows the relevant area guide and this file.
2. Tests were added or updated and pass.
3. Lint, type checks and build pass in the touched area, and you ran them.
4. No security rule in section 9 is violated.
5. The API contract is unchanged, or was updated in both guides with the user informed.
6. Docs are updated where behavior or setup changed.
7. The work is summarized for the user, including anything left unfinished or any assumption made.

## 12. When Unsure

Prefer the conservative option: ask, read the guide again, or make the smaller change. Report uncertainty plainly instead of hiding it.
