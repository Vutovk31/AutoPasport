from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_storage_usage_endpoint_requires_authentication():
    import app.main as main

    response = TestClient(main.app).get("/api/me/storage")
    assert response.status_code == 401


def test_storage_usage_endpoint_returns_owner_read_model(monkeypatch):
    import app.main as main

    expected = {
        "attachments": 2,
        "bytes_used": 25,
        "max_attachments": 100,
        "max_bytes": 262_144_000,
        "attachments_remaining": 98,
        "bytes_remaining": 262_143_975,
        "attachments_percent": 2.0,
        "bytes_percent": 0.0,
    }
    captured = {}

    def fake_usage(session, owner_id):
        captured["session"] = session
        captured["owner_id"] = owner_id
        return expected

    monkeypatch.setattr(main, "owner_storage_usage", fake_usage)
    session = object()
    result = main.my_storage_usage(SimpleNamespace(id="owner-1"), session)

    assert result == expected
    assert captured == {"session": session, "owner_id": "owner-1"}


def test_storage_usage_endpoint_is_in_openapi():
    import app.main as main

    operation = main.app.openapi()["paths"]["/api/me/storage"]["get"]
    assert operation["tags"] == ["account"]
