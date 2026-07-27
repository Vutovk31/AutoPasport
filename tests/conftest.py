from __future__ import annotations

import sys
from types import ModuleType

import pytest


def _dispose_database_engine() -> None:
    database = sys.modules.get("app.database")
    engine = getattr(database, "engine", None) if database else None
    if engine is not None:
        engine.dispose()


def _purge_app_modules() -> None:
    """Remove cached application modules and stale package attributes.

    Test modules rebuild AutoPassport against per-test environment variables.
    Removing only entries from ``sys.modules`` is insufficient because the
    parent ``app`` package can retain attributes pointing at old modules.
    """
    _dispose_database_engine()
    package = sys.modules.get("app")
    module_names = [name for name in sys.modules if name == "app" or name.startswith("app.")]

    for name in sorted(module_names, key=len, reverse=True):
        if name == "app":
            continue
        sys.modules.pop(name, None)
        if isinstance(package, ModuleType):
            attribute = name.split(".", 1)[1].split(".", 1)[0]
            package.__dict__.pop(attribute, None)


@pytest.fixture(autouse=True)
def isolate_application_modules():
    """Guarantee a fresh database/configuration graph for every test."""
    _purge_app_modules()
    yield
    _purge_app_modules()
