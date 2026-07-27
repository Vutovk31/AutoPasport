import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def prepare_app(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "storage"))
    monkeypatch.setenv("BACKUP_PATH", str(tmp_path / "backups"))
    monkeypatch.setenv("ADMIN_BACKUP_TOKEN", "test-token")

    env = os.environ.copy()
    env.update({
        "DATABASE_URL": f"sqlite:///{tmp_path / 'test.db'}",
        "STORAGE_PATH": str(tmp_path / "storage"),
        "BACKUP_PATH": str(tmp_path / "backups"),
        "ADMIN_BACKUP_TOKEN": "test-token",
    })
    migration = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert migration.returncode == 0, migration.stderr

    for module in ["app.main", "app.models", "app.database"]:
        sys.modules.pop(module, None)
    import app.main
    return app.main


def test_pwa_routes_and_private_cache_policy(tmp_path, monkeypatch):
    main = prepare_app(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        page = client.get("/")
        manifest = client.get("/manifest.webmanifest")
        worker = client.get("/service-worker.js")
        offline = client.get("/offline.html")

    assert page.status_code == 200
    assert 'rel="manifest"' in page.text
    assert "serviceWorker.register('/service-worker.js')" in client.get("/static/main.js").text

    assert manifest.status_code == 200
    body = manifest.json()
    assert body["display"] == "standalone"
    assert body["scope"] == "/"
    assert len(body["icons"]) >= 2

    assert worker.status_code == 200
    assert "CACHE_NAME = 'autopassport-shell-v0.23.0'" in worker.text
    assert "pathname.startsWith('/api/')" in worker.text
    assert "pathname.endsWith('/pdf')" in worker.text
    assert "pathname.startsWith('/storage/')" in worker.text

    assert offline.status_code == 200
    assert "Нет соединения" in offline.text


def test_release_files_exist_and_are_consistent():
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    assert (root / "Dockerfile").exists()
    assert (root / "docker-compose.yml").exists()
    assert (root / ".github/workflows/ci.yml").exists()
    assert (root / "docs/RELEASE_RUNBOOK.md").exists()

    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    ci = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "scripts/entrypoint.sh" in dockerfile
    assert "alembic upgrade head" in (root / "scripts/entrypoint.sh").read_text(encoding="utf-8")
    assert "/ready" in compose
    assert "pytest -q" in ci
    assert "docker compose config -q" in ci


def test_version_consistency(tmp_path, monkeypatch):
    main = prepare_app(tmp_path, monkeypatch)
    with TestClient(main.app) as client:
        assert client.get("/health").json()["version"] == "0.24.0"
        assert client.get("/ready").status_code == 200
    assert Path("VERSION").read_text(encoding="utf-8").strip() == "0.24.0"
