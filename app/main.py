"""FastAPI composition root.

The existing application routes live in app.application. This module adds
small cross-cutting API surfaces without expanding the legacy monolith.
"""

from pathlib import Path

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .application import *  # noqa: F401,F403
from .confirmed_visit_page import router as confirmed_visit_page_router
from .document_draft_confirm_api import router as document_draft_confirm_router
from .document_draft_review_api import router as document_draft_review_router
from .document_file_api import router as document_file_router
from .document_inbox_api import router as document_inbox_router
from .document_review_page import router as document_review_page_router
from .document_storage_health import router as document_storage_health_router
from .security import current_user, db
from .storage_quota import owner_storage_usage
from .share_limits import ShareQuotaExceeded, active_share_links, owner_share_usage

APP_VERSION = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
if not APP_VERSION:
    raise RuntimeError("VERSION must not be empty")
app.version = APP_VERSION
app.include_router(document_inbox_router)
app.include_router(document_draft_review_router)
app.include_router(document_draft_confirm_router)
app.include_router(document_file_router)
app.include_router(document_review_page_router)
app.include_router(confirmed_visit_page_router)
app.include_router(document_storage_health_router)
app.router.routes = [route for route in app.router.routes if getattr(route, "path", None) != "/health"]

@app.get("/health", tags=["operations"])
def health():
    return {"status": "ok", "version": APP_VERSION}

@app.exception_handler(ShareQuotaExceeded)
async def share_quota_error(_request: Request, exc: ShareQuotaExceeded):
    return JSONResponse(status_code=409, content={"detail": {"code": exc.code, "message": exc.message}})

@app.get("/api/me/storage", tags=["account"])
def my_storage_usage(user: User = Depends(current_user), session: Session = Depends(db)):
    return owner_storage_usage(session, user.id)

@app.get("/api/me/shares", tags=["account"])
def my_share_usage(user: User = Depends(current_user), session: Session = Depends(db)):
    return owner_share_usage(session, user.id)

@app.get("/api/me/shares/list", tags=["account"])
def my_active_share_links(user: User = Depends(current_user), session: Session = Depends(db)):
    return {"links": active_share_links(session, user.id)}
