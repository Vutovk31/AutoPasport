"""FastAPI composition root.

The existing application routes live in app.application. This module adds
small cross-cutting API surfaces without expanding the legacy monolith.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from .application import *  # noqa: F401,F403
from .security import current_user, db
from .storage_quota import owner_storage_usage


@app.get("/api/me/storage", tags=["account"])
def my_storage_usage(
    user: User = Depends(current_user),
    session: Session = Depends(db),
):
    """Return owner-wide active attachment usage and configured limits."""
    return owner_storage_usage(session, user.id)
