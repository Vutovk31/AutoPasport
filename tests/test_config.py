from __future__ import annotations

from pathlib import Path

from app.config import RuntimeConfig, validate_runtime_config


def config(**overrides):
    values = {
        "environment": "development",
        "database_url": "sqlite:///./data/autopassport.db",
        "storage_path": Path("data/storage"),
        "backup_path": Path("data/backups"),
        "public_base_url": "http://127.0.0.1:8000",
        "admin_backup_token": "",
        "cookie_secure": False,
        "max_upload_bytes": 5 * 1024 * 1024,
        "max_owner_attachments": 100,
        "max_owner_storage_bytes": 250 * 1024 * 1024,
    }
    values.update(overrides)
    return RuntimeConfig(**values)


def test_development_defaults_are_valid():
    assert validate_runtime_config(config()) == []


def test_production_requires_https_secure_cookie_and_strong_token():
    errors = validate_runtime_config(config(environment="production", admin_backup_token="change-me"))
    assert "Production PUBLIC_BASE_URL must use HTTPS" in errors
    assert "Production COOKIE_SECURE must be true" in errors
    assert "Production ADMIN_BACKUP_TOKEN must contain at least 32 characters" in errors
    assert "Production ADMIN_BACKUP_TOKEN must not use a documented default" in errors
    assert "Production DATABASE_URL must use an absolute SQLite path or external database" in errors


def test_production_configuration_can_pass():
    candidate = config(
        environment="production",
        database_url="sqlite:////app/data/autopassport.db",
        public_base_url="https://autopassport.example",
        admin_backup_token="x" * 48,
        cookie_secure=True,
    )
    assert validate_runtime_config(candidate) == []


def test_storage_and_backup_directories_must_differ():
    errors = validate_runtime_config(config(storage_path=Path("data/shared"), backup_path=Path("data/shared")))
    assert "STORAGE_PATH and BACKUP_PATH must be different directories" in errors


def test_mvp_upload_limit_is_bounded():
    errors = validate_runtime_config(config(max_upload_bytes=26 * 1024 * 1024))
    assert "MAX_UPLOAD_BYTES must not exceed 25 MiB in MVP" in errors


def test_owner_quota_bounds_are_validated():
    errors = validate_runtime_config(
        config(
            max_owner_attachments=1001,
            max_owner_storage_bytes=6 * 1024 * 1024 * 1024,
        )
    )
    assert "MAX_OWNER_ATTACHMENTS must not exceed 1000 in MVP" in errors
    assert "MAX_OWNER_STORAGE_BYTES must not exceed 5 GiB in MVP" in errors


def test_owner_storage_quota_cannot_be_smaller_than_single_upload_limit():
    errors = validate_runtime_config(
        config(max_upload_bytes=10 * 1024 * 1024, max_owner_storage_bytes=5 * 1024 * 1024)
    )
    assert "MAX_OWNER_STORAGE_BYTES must be at least MAX_UPLOAD_BYTES" in errors
