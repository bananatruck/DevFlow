"""FastAPI routes.

Endpoints (MVP):
- POST /runs          -> enqueue agent run
- GET  /runs/{id}     -> get status
- GET  /runs/{id}/artifacts -> fetch plan/checklist/summary

Implementation note:
- Use Redis queue for long-running runs
- Persist durable logs & artifacts in Postgres
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# TODO: Add /runs endpoints backed by queue + DB
