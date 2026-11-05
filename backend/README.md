# MarketPilot backend

FastAPI service and multi-agent pipeline for MarketPilot. Setup and workflow rules
live in [agent.md](./agent.md).

## Quick start

```bash
uv sync
uv run uvicorn app.main:app --reload
uv run pytest
```

## Configuration

Settings load from the environment, and a local `.env` file if present. Startup
fails with a validation error naming any missing required variable.

Required: `DEEPSEEK_API_KEY`, `DATABASE_URL`, `REDIS_URL`.

Optional with defaults: `DEEPSEEK_BASE_URL`, `IMAGE_PROVIDER` (`fake`, `flux`,
`sdxl`), `COST_CAP_PER_RUN`, `MAX_IMAGE_CALLS_PER_RUN`,
`MAX_SEARCH_CALLS_PER_RUN`, `RETRY_MAX_ATTEMPTS`, `FRONTEND_ORIGIN`, `LOG_LEVEL`.

