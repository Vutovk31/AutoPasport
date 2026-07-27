from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from urllib.parse import urlparse


class ConfigurationError(RuntimeError):
    """Raised when runtime configuration is unsafe or inconsistent."""


@dataclass(frozen=True)
class RuntimeConfig:
    environment: str
    database_url: str
    storage_path: Path
    backup_path: Path
    public_base_url: str
    admin_backup_token: str
    cookie_secure: bool
    max_upload_bytes: int

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def _required_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value


def load_runtime_config() -> RuntimeConfig:
    environment = os.getenv("APP_ENV", "development").strip().lower()
    if environment not in {"development", "test", "production"}:
        raise ConfigurationError("APP_ENV must be development, test or production")

    return RuntimeConfig(
        environment=environment,
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/autopassport.db").strip(),
        storage_path=Path(os.getenv("STORAGE_PATH", "./data/storage")).expanduser(),
        backup_path=Path(os.getenv("BACKUP_PATH", "./data/backups")).expanduser(),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/"),
        admin_backup_token=os.getenv("ADMIN_BACKUP_TOKEN", "").strip(),
        cookie_secure=os.getenv("COOKIE_SECURE", "false").strip().lower() == "true",
        max_upload_bytes=_required_int("MAX_UPLOAD_BYTES", 5 * 1024 * 1024),
    )


def validate_runtime_config(config: RuntimeConfig) -> list[str]:
    errors: list[str] = []

    if not config.database_url:
        errors.append("DATABASE_URL is required")
    if not config.public_base_url:
        errors.append("PUBLIC_BASE_URL is required")
    else:
        parsed = urlparse(config.public_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append("PUBLIC_BASE_URL must be an absolute http(s) URL")

    if config.storage_path.resolve() == config.backup_path.resolve():
        errors.append("STORAGE_PATH and BACKUP_PATH must be different directories")

    if config.max_upload_bytes > 25 * 1024 * 1024:
        errors.append("MAX_UPLOAD_BYTES must not exceed 25 MiB in MVP")

    if config.is_production:
        if not config.public_base_url.startswith("https://"):
            errors.append("Production PUBLIC_BASE_URL must use HTTPS")
        if not config.cookie_secure:
            errors.append("Production COOKIE_SECURE must be true")
        if len(config.admin_backup_token) < 32:
            errors.append("Production ADMIN_BACKUP_TOKEN must contain at least 32 characters")
        if config.admin_backup_token in {"change-me", "ci-admin-token"}:
            errors.append("Production ADMIN_BACKUP_TOKEN must not use a documented default")
        if config.database_url.startswith("sqlite:///./"):
            errors.append("Production DATABASE_URL must use an absolute SQLite path or external database")

    return errors


def assert_runtime_config() -> RuntimeConfig:
    config = load_runtime_config()
    errors = validate_runtime_config(config)
    if errors:
        raise ConfigurationError("; ".join(errors))
    return config
