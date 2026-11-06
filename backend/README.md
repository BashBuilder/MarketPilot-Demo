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
`hosted`, `huggingface`), `IMAGE_API_URL`, `IMAGE_API_KEY`, `IMAGE_MODEL_ID`,
`IMAGE_TIMEOUT_SECONDS`, `SEARCH_PROVIDER`, `EMBEDDER` (`fake`, `huggingface`),
`HF_EMBEDDING_MODEL`, `HUGGINGFACEHUB_API_TOKEN`, `ASSET_STORAGE` (`local`,
`cloudinary`), `ASSET_DIR`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`,
`CLOUDINARY_API_SECRET`, `CLOUDINARY_FOLDER`, `CLOUDINARY_TIMEOUT_SECONDS`,
`COST_CAP_PER_RUN`, `MAX_IMAGE_CALLS_PER_RUN`, `MAX_GENERATED_IMAGES_PER_RUN`,
`MAX_SEARCH_CALLS_PER_RUN`, `MAX_IMAGE_PROMPT_LENGTH`, `RETRY_MAX_ATTEMPTS`,
`SCORE_THRESHOLD`, `MAX_AUTO_LOOPS`, `MAX_IDEA_LENGTH`, `MAX_COMMENT_LENGTH`,
`RATE_LIMIT_PER_MINUTE`, `MAX_CONCURRENT_RUNS`, `TRUST_PROXY`,
`FRONTEND_ORIGIN`, `LOG_LEVEL`. `.env.example` lists every one; a test keeps
the two in sync.

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
network or model files. `hosted` calls `IMAGE_API_URL` (Bearer `IMAGE_API_KEY`).
`huggingface` calls Hugging Face Inference Providers over HTTP with
`HUGGINGFACEHUB_API_TOKEN` and `IMAGE_MODEL_ID`. Both remote providers download
and run nothing locally. `IMAGE_TIMEOUT_SECONDS` (default 45) is a total
per-image deadline enforced by both adapters. `huggingface` does not support
`edit_image`; use `hosted` when the compliance loop must revise an existing
asset. Janus is not available through the serverless `hf-inference` router; to
use it without local weights, deploy a dedicated Hugging Face Inference Endpoint
and point `IMAGE_API_URL` at it.

Startup seeds the policy documents and re-embeds them when `EMBEDDER` changes.
`EMBEDDER=fake` is the default and needs no model files. `EMBEDDER=huggingface`
requires `uv sync --extra embeddings`, a `HUGGINGFACEHUB_API_TOKEN`, and network
access to the HuggingFace Inference API. The default hosted model is
`sentence-transformers/all-MiniLM-L6-v2`; no model is downloaded or run locally.

## Asset storage

Generation always writes a local working copy under `ASSET_DIR`. `ASSET_STORAGE`
decides what URI the campaign package records:

- `local` (default) stores the relative path, so images are only readable by
  this process. Suitable for development; container disks are ephemeral.
- `cloudinary` uploads each file and stores the returned `secure_url`. The URL
  is saved both in the package (`assets[].uri` on
  `GET /campaigns/{id}/versions/{n}`) and in the `assets` table for the version,
  so the frontend can load it directly. Uploads are content-addressed by
  checksum, so retries do not duplicate assets. A revision seeded from a stored
  package downloads the source back before editing it.

`cloudinary` requires `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` and
`CLOUDINARY_API_SECRET`; startup fails if any is missing. Once a version stores
a remote URL, the `export_package` tool (filesystem-only today) cannot copy it.

## Deployment

The service is a plain Python process: no Dockerfile is required. On Render use
the Python runtime with `backend` as the root directory:

```bash
# build
pip install uv && uv sync --frozen --no-dev
# pre-deploy (schema must exist before startup seeds policies)
uv run --no-dev alembic upgrade head
# start
uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set `ASSET_STORAGE=cloudinary`, `TRUST_PROXY=true`, the Cloudinary credentials,
the Render Postgres/Key Value URLs and the deployed `FRONTEND_ORIGIN`. Use the
HTTP health check at `/health`.

## Image model benchmark

`benchmarks/image_models.py` compares remote open-weight text-to-image models on
five fixed prompts. It calls Hugging Face Inference Providers (`hf-inference`);
no model weights are downloaded. A live run needs `HUGGINGFACEHUB_API_TOKEN` and
asks for confirmation before making any requests. Janus is not offered by
`hf-inference`; use a dedicated hosted endpoint if you need it.

```bash
uv run python -m benchmarks.image_models --dry-run
uv run python -m benchmarks.image_models --model stabilityai/sdxl-turbo --yes
```

Images go to `$ASSET_DIR/benchmarks/<model>/` and the report to
`benchmarks/results.md`. Quality and licence columns are left blank for manual
review. `--dry-run` uses the deterministic fake backend and needs no token.

