"""FastAPI application entrypoint."""

from fastapi import FastAPI

app = FastAPI(title="MarketPilot API", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Report liveness for container orchestration and load balancers."""
    return {"status": "ok"}
