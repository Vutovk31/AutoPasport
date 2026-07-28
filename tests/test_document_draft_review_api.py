from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient


DEMO_VIN = "DEMO-REVIEW-00001"


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


def create_reviewable_draft(client, vehicle_id):
    uploaded = client.post(
        f"/api/vehicles/{vehicle_id}/documents",
        headers=csrf(client),
        data={"document_type": "work_order"},
        files={"file": ("order.pdf", b"%PDF-1.4 order data", "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    document_id = uploaded.json()["id"]
    draft = client.post(
        f"/api/documents/{document_id}/draft",
        headers=csrf(client),
        json={
            "extracted_text": "Пробег 178000 км",
            "proposed_fields": {"mileage": 178000, "service_name": "Неизвестный сервис"},
            "confidence": {"mileage": 0.74, "service_name": 0.41},
            "parser_name": "contract-test",
            "parser_version": "1.0",
        },
    )
    assert draft.status_code == 201, draft.text
    return document_id


def test_owner_can_correct_reviewable_draft_without_history_mutation(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        register(client)
        vehicle_id = create_vehicle(client)
        document_id = create_reviewable_draft(client, vehicle_id)

        corrected = client.patch(
            f"/api/documents/{document_id}/draft/review",
            headers=csrf(client),
            json={
                "extracted_text": "Пробег 178711 км. Сервис АвтоПлюс.",
                "proposed_fields": {"mileage": 178711, "service_name": "АвтоПлюс", "total_cost_rubles": 4800},
                "confidence": {"mileage": 1.0, "service_name": 1.0, "total_cost_rubles": 1.0},
            },
        )

        assert corrected.status_code == 200, corrected.text
        payload = corrected.json()
        assert payload["status"] == "needs_review"
        assert payload["proposed_fields"]["mileage"] == 178711
        assert payload["proposed_fields"]["service_name"] == "АвтоПлюс"
        assert payload["confidence"]["service_name"] == 1.0

        fetched = client.get(f"/api/documents/{document_id}/draft")
        assert fetched.status_code == 200
        assert fetched.json() == payload
        detail = client.get(f"/api/vehicles/{vehicle_id}").json()
        assert detail["events"] == []
        assert detail["visits"] == []


def test_partial_review_preserves_unchanged_fields(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        register(client)
        vehicle_id = create_vehicle(client)
        document_id = create_reviewable_draft(client, vehicle_id)

        corrected = client.patch(
            f"/api/documents/{document_id}/draft/review",
            headers=csrf(client),
            json={"proposed_fields": {"mileage": 178711}},
        )

        assert corrected.status_code == 200, corrected.text
        payload = corrected.json()
        assert payload["proposed_fields"] == {"mileage": 178711}
        assert payload["confidence"] == {"mileage": 0.74, "service_name": 0.41}
        assert payload["extracted_text"] == "Пробег 178000 км"


def test_invalid_confidence_and_other_owner_are_rejected(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as owner, TestClient(main.app) as intruder:
        register(owner, "owner@example.com")
        vehicle_id = create_vehicle(owner)
        document_id = create_reviewable_draft(owner, vehicle_id)

        invalid = owner.patch(
            f"/api/documents/{document_id}/draft/review",
            headers=csrf(owner),
            json={"confidence": {"mileage": 1.5}},
        )
        assert invalid.status_code == 422

        register(intruder, "intruder@example.com")
        forbidden = intruder.patch(
            f"/api/documents/{document_id}/draft/review",
            headers=csrf(intruder),
            json={"proposed_fields": {"mileage": 1}},
        )
        assert forbidden.status_code == 403
