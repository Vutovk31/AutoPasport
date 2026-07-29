"""Unified readiness probe for mandatory AutoPassport dependencies."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .database import SessionLocal
from .document_storage import DocumentStorageError
from .document_storage_health import probe_document_storage

router = APIRouter()


def probe_database() -> dict[str, str]:
    """Verify that the configured database accepts a minimal query."""

    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except Exception as error:
        raise RuntimeError("Database readiness probe failed") from error

    return {"status": "ok"}


def probe_application_readiness(version: str) -> tuple[dict, int]:
    """Return component-level readiness without exposing internal errors."""

    components: dict[str, dict[str, str]] = {}
    ready = True

    try:
        components["database"] = probe_database()
    except RuntimeError:
        ready = False
        components["database"] = {
            "status": "unavailable",
            "detail": "Database readiness probe failed",
        }

    try:
        storage = probe_document_storage()
        components["storage"] = {
            "status": storage["status"],
            "backend": storage["backend"],
        }
    except DocumentStorageError:
        ready = False
        components["storage"] = {
            "status": "unavailable",
            "detail": "Document storage readiness probe failed",
        }

    payload = {
        "status": "ready" if ready else "unavailable",
        "version": version,
        "components": components,
    }
    return payload, 200 if ready else 503


@router.get("/ready", tags=["operations"])
def readiness():
    from .main import APP_VERSION

    payload, status_code = probe_application_readiness(APP_VERSION)
    if status_code == 200:
        return payload
    return JSONResponse(status_code=status_code, content=payload)
