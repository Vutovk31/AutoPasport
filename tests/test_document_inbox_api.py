from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient


DEMO_VIN = "DEMO-DOC-00000001"


def load_app(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    storage_path = tmp_path / "storage"
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": database_url,
            "STORAGE_PATH": str(storage_path),
            "PUBLIC_BASE_URL": "http://testserver",
        }
    )
    migrated = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert migrated.returncode == 0, migrated.stderr

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("STORAGE_PATH", str(storage_path))
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://testserver")

    import app.main

    return app.main, storage_path


def csrf(client):
    return {"X-CSRF-Token": client.cookies.get("autopassport_csrf")}


def register(client, email="owner@example.com"):
    response = client.post(
        "/api/auth/register",
        data={"email": email, "password": "StrongPassword123"},
    )
    assert response.status_code == 201, response.text


def create_vehicle(client):
    response = client.post(
        "/api/vehicles",
        headers=csrf(client),
        data={
            "vin": DEMO_VIN,
            "registration_number": "TEST",
            "make": "Mazda",
            "model": "3 BK",
            "trim": "",
            "year": 2006,
            "current_mileage": 178711,
            "purchase_date": "",
            "purchase_mileage": "",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_upload_persists_unprocessed_document_without_history_mutation(tmp_path, monkeypatch):
    main, storage_path = load_app(tmp_path, monkeypatch)
    content = b"%PDF-1.4 order data"

    with TestClient(main.app) as client:
        register(client)
        vehicle_id = create_vehicle(client)
        uploaded = client.post(
            f"/api/vehicles/{vehicle_id}/documents",
            headers=csrf(client),
            data={"document_type": "work_order"},
            files={"file": ("../../order.pdf", content, "application/pdf")},
        )

        assert uploaded.status_code == 201, uploaded.text
        payload = uploaded.json()
        assert payload["vehicle_id"] == vehicle_id
        assert payload["document_type"] == "work_order"
        assert payload["original_name"] == "order.pdf"
        assert payload["status"] == "uploaded"
        assert payload["linked_visit_id"] is None
        assert payload["failure_reason"] is None
        assert payload["sha256"] == hashlib.sha256(content).hexdigest()
        assert payload["size_bytes"] == len(content)

        listed = client.get(f"/api/vehicles/{vehicle_id}/documents")
        assert listed.status_code == 200
        assert listed.json()["documents"] == [payload]

        detail = client.get(f"/api/vehicles/{vehicle_id}").json()
        assert detail["events"] == []
        assert detail["visits"] == []

    stored_files = list((storage_path / "document_inbox").iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == content


def test_spoofed_document_is_rejected_without_file_or_database_record(tmp_path, monkeypatch):
    main, storage_path = load_app(tmp_path, monkeypatch)

    with TestClient(main.app) as client:
        register(client)
        vehicle_id = create_vehicle(client)
        rejected = client.post(
            f"/api/vehicles/{vehicle_id}/documents",
            headers=csrf(client),
            data={"document_type": "receipt"},
            files={"file": ("receipt.jpg", b"%PDF-not-a-jpeg", "image/jpeg")},
        )

        assert rejected.status_code == 415
        listed = client.get(f"/api/vehicles/{vehicle_id}/documents")
        assert listed.json() == {"documents": []}

    inbox_path = storage_path / "document_inbox"
    assert not inbox_path.exists() or list(inbox_path.iterdir()) == []


def test_other_owner_cannot_upload_or_list_vehicle_documents(tmp_path, monkeypatch):
    main, _ = load_app(tmp_path, monkeypatch)

    with TestClient(main.app) as owner, TestClient(main.app) as intruder:
        register(owner, "owner@example.com")
        vehicle_id = create_vehicle(owner)
        register(intruder, "intruder@example.com")

        uploaded = intruder.post(
            f"/api/vehicles/{vehicle_id}/documents",
            headers=csrf(intruder),
            data={"document_type": "work_order"},
            files={"file": ("order.pdf", b"%PDF-1.4 data", "application/pdf")},
        )
        listed = intruder.get(f"/api/vehicles/{vehicle_id}/documents")

        assert uploaded.status_code == 403
        assert listed.status_code == 403
