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

Optional with defaults: `DEEPSEEK_BASE_URL`, `EVENT_STREAM_MAXLEN`,
`EVENT_STREAM_TTL_SECONDS`, `RESUME_ON_STARTUP`, `IMAGE_PROVIDER` (`fake`,
`hosted`, `local`), `IMAGE_API_URL`, `IMAGE_API_KEY`, `IMAGE_MODEL_ID`,
`IMAGE_TIMEOUT_SECONDS`, `EMBEDDER` (`fake`, `huggingface`),
`HF_EMBEDDING_MODEL`, `HUGGINGFACEHUB_API_TOKEN`, `COST_CAP_PER_RUN`,
`MAX_IMAGE_CALLS_PER_RUN`, `MAX_GENERATED_IMAGES_PER_RUN`,
`MAX_SEARCH_CALLS_PER_RUN`, `RETRY_MAX_ATTEMPTS`,
`SCORE_THRESHOLD`, `MAX_AUTO_LOOPS`, `MAX_IDEA_LENGTH`, `MAX_COMMENT_LENGTH`,
`RATE_LIMIT_PER_MINUTE`, `MAX_CONCURRENT_RUNS`, `TRUST_PROXY`,
`FRONTEND_ORIGIN`, `LOG_LEVEL`.

`RATE_LIMIT_PER_MINUTE` (default 20) limits writes per client IP; reads get
five times that budget. Set `TRUST_PROXY=true` only behind a proxy that sets
`X-Forwarded-For`, otherwise the header is ignored. `MAX_CONCURRENT_RUNS`
(default 3) rejects new campaigns and revisions with `429 too_many_runs` while
that many runs are executing.

Each run's Redis stream is capped at `EVENT_STREAM_MAXLEN` entries and expires
`EVENT_STREAM_TTL_SECONDS` after a terminal event. With
`RESUME_ON_STARTUP=true`, startup claims runs left `running` with a short Redis
lock and resumes them from the latest checkpoint; one failed resume is logged
and does not block the others or the app from starting.

`IMAGE_PROVIDER=fake` is the default and writes deterministic PNGs with no
network or model files. `hosted` calls `IMAGE_API_URL` (Bearer `IMAGE_API_KEY`)
and needs no local model. `local` runs a diffusers pipeline on this machine and
requires `uv sync --extra images`; weights are downloaded from the model hub on
first use, so tests never select it.

Startup seeds the policy documents and re-embeds them when `EMBEDDER` changes.
`EMBEDDER=fake` is the default and needs no model files. `EMBEDDER=huggingface`
requires `uv sync --extra embeddings`, a `HUGGINGFACEHUB_API_TOKEN`, and network
access to the HuggingFace Inference API. The default hosted model is
`sentence-transformers/all-MiniLM-L6-v2`; no model is downloaded or run locally.

## Image model benchmark

`benchmarks/image_models.py` compares remote open-weight text-to-image models on
five fixed prompts. It calls Hugging Face Inference Providers (`hf-inference`);
no model weights are downloaded. A live run needs `HUGGINGFACEHUB_API_TOKEN` and
asks for confirmation before making any requests.

```bash
uv run python -m benchmarks.image_models --dry-run
uv run python -m benchmarks.image_models --model stabilityai/sdxl-turbo --yes
```

Images go to `$ASSET_DIR/benchmarks/<model>/` and the report to
`benchmarks/results.md`. Quality and licence columns are left blank for manual
review. `--dry-run` uses the deterministic fake backend and needs no token.

