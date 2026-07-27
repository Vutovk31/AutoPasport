# Decision Log

## ADR-060 — PDF uses public/private payload boundary

Приватный PDF владельца может показывать полный VIN. Публичный PDF всегда строится через публичный payload с маскированным VIN.

## ADR-061 — Backup includes database and storage together

История без документов неполноценна, поэтому SQLite и storage архивируются одним backup.

## ADR-062 — Backup requires explicit admin token

MVP использует отдельный `ADMIN_BACKUP_TOKEN`, чтобы не открывать backup через обычный пользовательский интерфейс.


## ADR-063 — PWA shell caches no private data
The service worker caches only static app shell assets. API payloads, PDF files and storage content stay network-only to avoid leaking vehicle history in browser cache.

## ADR-064 — Container startup runs migrations
The Docker entrypoint applies `alembic upgrade head` before starting the ASGI server.

## ADR-065 — Release readiness includes CI and Docker validation
A version is not release-ready unless tests, migrations and docker-compose config are validated.

## ADR-066 — Backup archive is untrusted input

Любой backup ZIP проверяется на безопасные пути, контрольные суммы и SQLite integrity до восстановления.

## ADR-067 — Restore uses staging first

AutoPassport распаковывает backup во временный staging-каталог и заменяет целевую директорию только после успешной проверки.
