from __future__ import annotations

from pathlib import Path

from app.config import RuntimeConfig, validate_runtime_config


def config(**overrides):
    values = {
        "environment": "development",
        "database_url": "sqlite:///./data/autopassport.db",
        "storage_path": Path("data/storage"),
        "storage_backend": "local",
        "s3_bucket": "",
        "s3_endpoint_url": "",
        "s3_region": "",
        "s3_prefix": "",
        "backup_path": Path("data/backups"),
        "public_base_url": "http://127.0.0.1:8000",
        "admin_backup_token": "",
        "cookie_secure": False,
        "max_upload_bytes": 5 * 1024 * 1024,
        "max_owner_attachments": 100,
        "max_owner_storage_bytes": 250 * 1024 * 1024,
        "max_active_share_links_per_vehicle": 1,
        "max_active_share_links_per_owner": 10,
        "attachment_retention_days": 30,
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


def test_storage_and_backup_directories_must_differ_for_local_backend():
    errors = validate_runtime_config(config(storage_path=Path("data/shared"), backup_path=Path("data/shared")))
    assert "STORAGE_PATH and BACKUP_PATH must be different directories" in errors


def test_s3_backend_requires_bucket():
    errors = validate_runtime_config(config(storage_backend="s3"))
    assert "S3_BUCKET is required for STORAGE_BACKEND=s3" in errors


def test_s3_backend_accepts_private_https_endpoint_and_safe_prefix():
    candidate = config(
        storage_backend="s3",
        s3_bucket="autopassport-private",
        s3_endpoint_url="https://storage.example.com",
        s3_region="ru-central1",
        s3_prefix="documents/production",
    )
    assert validate_runtime_config(candidate) == []


def test_s3_prefix_rejects_path_traversal():
    errors = validate_runtime_config(
        config(storage_backend="s3", s3_bucket="autopassport-private", s3_prefix="documents/../private")
    )
    assert "S3_PREFIX must be a safe relative object prefix" in errors


def test_s3_endpoint_must_be_absolute_and_https_in_production():
    malformed = validate_runtime_config(
        config(storage_backend="s3", s3_bucket="bucket", s3_endpoint_url="storage.example.com")
    )
    assert "S3_ENDPOINT_URL must be an absolute http(s) URL" in malformed

    production = validate_runtime_config(
        config(
            environment="production",
            database_url="sqlite:////app/data/autopassport.db",
            public_base_url="https://autopassport.example",
            admin_backup_token="x" * 48,
            cookie_secure=True,
            storage_backend="s3",
            s3_bucket="bucket",
            s3_endpoint_url="http://storage.example.com",
        )
    )
    assert "Production S3_ENDPOINT_URL must use HTTPS" in production


def test_unknown_storage_backend_is_rejected():
    errors = validate_runtime_config(config(storage_backend="azure"))
    assert "STORAGE_BACKEND must be local or s3" in errors


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


def test_share_limits_are_bounded_and_consistent():
    errors = validate_runtime_config(
        config(max_active_share_links_per_vehicle=11, max_active_share_links_per_owner=5)
    )
    assert "MAX_ACTIVE_SHARE_LINKS_PER_VEHICLE must not exceed 10 in MVP" in errors
    assert "MAX_ACTIVE_SHARE_LINKS_PER_OWNER must be at least MAX_ACTIVE_SHARE_LINKS_PER_VEHICLE" in errors


def test_attachment_retention_period_is_bounded():
    errors = validate_runtime_config(config(attachment_retention_days=3651))
    assert "ATTACHMENT_RETENTION_DAYS must not exceed 3650 days" in errors
