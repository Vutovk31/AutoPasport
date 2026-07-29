from pathlib import Path

from fastapi.responses import JSONResponse

from app.document_storage import DocumentStorageError
from app.readiness import probe_application_readiness, probe_database


class FakeSession:
    def __init__(self, error=None):
        self.error = error
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query):
        self.queries.append(str(query))
        if self.error:
            raise self.error


def test_database_probe_executes_select_one(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr("app.readiness.SessionLocal", lambda: session)

    assert probe_database() == {"status": "ok"}
    assert session.queries == ["SELECT 1"]


def test_readiness_reports_all_components(monkeypatch):
    monkeypatch.setattr("app.readiness.probe_database", lambda: {"status": "ok"})
    monkeypatch.setattr(
        "app.readiness.probe_document_storage",
        lambda: {"status": "ok", "backend": "s3"},
    )

    payload, status_code = probe_application_readiness("0.26.0")

    assert status_code == 200
    assert payload == {
        "status": "ready",
        "version": "0.26.0",
        "components": {
            "database": {"status": "ok"},
            "storage": {"status": "ok", "backend": "s3"},
        },
    }


def test_readiness_returns_503_when_database_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.readiness.probe_database",
        lambda: (_ for _ in ()).throw(RuntimeError("password leaked")),
    )
    monkeypatch.setattr(
        "app.readiness.probe_document_storage",
        lambda: {"status": "ok", "backend": "local"},
    )

    payload, status_code = probe_application_readiness("0.25.0")

    assert status_code == 503
    assert payload["status"] == "unavailable"
    assert payload["components"]["database"] == {
        "status": "unavailable",
        "detail": "Database readiness probe failed",
    }
    assert "password leaked" not in str(payload)


def test_readiness_returns_503_when_storage_is_unavailable(monkeypatch):
    monkeypatch.setattr("app.readiness.probe_database", lambda: {"status": "ok"})
    monkeypatch.setattr(
        "app.readiness.probe_document_storage",
        lambda: (_ for _ in ()).throw(DocumentStorageError("credentials leaked")),
    )

    payload, status_code = probe_application_readiness("0.25.0")

    assert status_code == 503
    assert payload["components"]["storage"] == {
        "status": "unavailable",
        "detail": "Document storage readiness probe failed",
    }
    assert "credentials leaked" not in str(payload)


def test_main_registers_readiness_router():
    source = Path("app/main.py").read_text(encoding="utf-8")

    assert "readiness_router" in source
    assert "app.include_router(readiness_router)" in source
    assert '@router.get("/ready"' in Path("app/readiness.py").read_text(encoding="utf-8")
