from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import domains

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Uptime Kuma Domain API",
    description=(
        "REST wrapper around Uptime Kuma's Socket.IO interface for managing "
        "domain (HTTP/HTTPS) monitors, e.g. from a CRM."
    ),
    version="1.0.0",
)

app.include_router(domains.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


# Human-readable API reference (design doc), separate from the auto-generated
# Swagger UI at /docs and ReDoc at /redoc.
app.mount("/reference", StaticFiles(directory=STATIC_DIR, html=True), name="reference")
