"""FastAPI composition root.

The existing application routes live in app.application. This module adds
small cross-cutting API surfaces without expanding the legacy monolith.
"""

from pathlib import Path

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .application import *  # noqa: F401,F403
from .security import current_user, db
from .storage_quota import owner_storage_usage
from .share_limits import ShareQuotaExceeded, active_share_links, owner_share_usage


APP_VERSION = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
if not APP_VERSION:
    raise RuntimeError("VERSION must not be empty")
app.version = APP_VERSION
app.router.routes = [route for route in app.router.routes if getattr(route, "path", None) != "/health"]


@app.get("/health", tags=["operations"])
def health():
    """Return the release version from the canonical VERSION file."""
    return {"status": "ok", "version": APP_VERSION}


@app.exception_handler(ShareQuotaExceeded)
async def share_quota_error(_request: Request, exc: ShareQuotaExceeded):
    return JSONResponse(status_code=409, content={"detail": {"code": exc.code, "message": exc.message}})


@app.get("/api/me/storage", tags=["account"])
def my_storage_usage(
    user: User = Depends(current_user),
    session: Session = Depends(db),
):
    """Return owner-wide active attachment usage and configured limits."""
    return owner_storage_usage(session, user.id)


@app.get("/api/me/shares", tags=["account"])
def my_share_usage(
    user: User = Depends(current_user),
    session: Session = Depends(db),
):
    """Return owner-wide active public-link usage and configured limit."""
    return owner_share_usage(session, user.id)


@app.get("/api/me/shares/list", tags=["account"])
def my_active_share_links(
    user: User = Depends(current_user),
    session: Session = Depends(db),
):
    """Return only active, non-revoked public links owned by the current user."""
    return {"links": active_share_links(session, user.id)}
