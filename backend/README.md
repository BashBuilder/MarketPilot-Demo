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
`sdxl`), `EMBEDDER` (`fake`, `huggingface`), `HF_EMBEDDING_MODEL`,
`HUGGINGFACEHUB_API_TOKEN`, `COST_CAP_PER_RUN`, `MAX_IMAGE_CALLS_PER_RUN`,
`MAX_SEARCH_CALLS_PER_RUN`, `RETRY_MAX_ATTEMPTS`, `SCORE_THRESHOLD`,
`MAX_AUTO_LOOPS`, `FRONTEND_ORIGIN`, `LOG_LEVEL`.

Startup seeds the policy documents and re-embeds them when `EMBEDDER` changes.
`EMBEDDER=fake` is the default and needs no model files. `EMBEDDER=huggingface`
requires `uv sync --extra embeddings`, a `HUGGINGFACEHUB_API_TOKEN`, and network
access to the HuggingFace Inference API. The default hosted model is
`sentence-transformers/all-MiniLM-L6-v2`; no model is downloaded or run locally.

