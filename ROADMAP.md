# Roadmap

## Завершено
- ServiceVisit / ServiceItem.
- Временный публичный паспорт.
- Контекстная trust-модель.
- PDF-паспорт владельца.
- Публичный PDF с маскированным VIN.
- QR-код временной публичной ссылки в PDF.
- Backup SQLite + storage.
- Проверка backup manifest и SHA-256.
- Restore smoke test.

## Следующий этап
- PWA.
- Docker.
- CI/CD.
- UX-полировка мобильного кабинета.


## 0.23.0 completed
- Installable PWA shell.
- Offline shell fallback.
- Dockerfile and docker-compose.
- GitHub Actions CI.

## Next
- Production hardening: admin roles, storage quotas, document antivirus scanning.
- Restore test with a separate app instance.

## v0.24.0 — Restore Hardening

- Безопасная распаковка backup без path traversal.
- SHA-256 базы данных внутри backup.
- Проверка SHA-256 каждого storage-файла.
- SQLite `PRAGMA integrity_check` перед восстановлением.
- Restore в staging-каталог с заменой цели только после проверки.
- Admin restore-check endpoint.
- Boot smoke восстановленного приложения через `/health` и `/ready`.
