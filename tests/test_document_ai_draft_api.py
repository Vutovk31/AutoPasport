from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient


DEMO_VIN = "DEMO-AI-000000001"


def load_app(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    storage_path = tmp_path / "storage"
    env = os.environ.copy()
    env.update({"DATABASE_URL": database_url, "STORAGE_PATH": str(storage_path), "PUBLIC_BASE_URL": "http://testserver"})
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
    return app.main


def csrf(client):
    return {"X-CSRF-Token": client.cookies.get("autopassport_csrf")}


def register(client, email="owner@example.com"):
    response = client.post("/api/auth/register", data={"email": email, "password": "StrongPassword123"})
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


def upload_document(client, vehicle_id):
    response = client.post(
        f"/api/vehicles/{vehicle_id}/documents",
        headers=csrf(client),
        data={"document_type": "work_order"},
        files={"file": ("order.pdf", b"%PDF-1.4 order data", "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_parser_result_becomes_reviewable_draft_without_history_mutation(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        register(client)
        vehicle_id = create_vehicle(client)
        document_id = upload_document(client, vehicle_id)
        created = client.post(
            f"/api/documents/{document_id}/draft",
            headers=csrf(client),
            json={
                "extracted_text": "Заказ-наряд. Пробег 178711 км.",
                "proposed_fields": {"mileage": 178711, "service_name": "Автосервис"},
                "confidence": {"mileage": 0.98, "service_name": 0.72},
                "parser_name": "manual-contract-test",
                "parser_version": "1.0",
            },
        )
        assert created.status_code == 201, created.text
        draft = created.json()
        assert draft["document_id"] == document_id
        assert draft["status"] == "needs_review"
        assert draft["proposed_fields"]["mileage"] == 178711
        assert draft["confidence"]["mileage"] == 0.98

        fetched = client.get(f"/api/documents/{document_id}/draft")
        assert fetched.status_code == 200
        assert fetched.json() == draft

        documents = client.get(f"/api/vehicles/{vehicle_id}/documents").json()["documents"]
        assert documents[0]["status"] == "needs_review"
        detail = client.get(f"/api/vehicles/{vehicle_id}").json()
        assert detail["events"] == []
        assert detail["visits"] == []


def test_duplicate_and_invalid_confidence_are_rejected(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        register(client)
        vehicle_id = create_vehicle(client)
        document_id = upload_document(client, vehicle_id)
        invalid = client.post(
            f"/api/documents/{document_id}/draft",
            headers=csrf(client),
            json={
                "extracted_text": "text",
                "proposed_fields": {},
                "confidence": {"mileage": 1.2},
                "parser_name": "parser",
                "parser_version": "1",
            },
        )
        assert invalid.status_code == 422

        payload = {
            "extracted_text": "text",
            "proposed_fields": {},
            "confidence": {},
            "parser_name": "parser",
            "parser_version": "1",
        }
        assert client.post(f"/api/documents/{document_id}/draft", headers=csrf(client), json=payload).status_code == 201
        assert client.post(f"/api/documents/{document_id}/draft", headers=csrf(client), json=payload).status_code == 409


def test_other_owner_cannot_read_or_create_document_draft(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as owner, TestClient(main.app) as intruder:
        register(owner, "owner@example.com")
        vehicle_id = create_vehicle(owner)
        document_id = upload_document(owner, vehicle_id)
        register(intruder, "intruder@example.com")
        payload = {
            "extracted_text": "text",
            "proposed_fields": {},
            "confidence": {},
            "parser_name": "parser",
            "parser_version": "1",
        }
        created = intruder.post(f"/api/documents/{document_id}/draft", headers=csrf(intruder), json=payload)
        fetched = intruder.get(f"/api/documents/{document_id}/draft")
        assert created.status_code == 403
        assert fetched.status_code == 403
