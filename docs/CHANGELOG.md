
# Changelog

## 0.23.0
- Added installable PWA app shell.
- Added root-scoped service worker with private API/PDF cache exclusion.
- Added offline shell page.
- Added PWA icons and web app manifest.
- Added Dockerfile and docker-compose release contour.
- Added GitHub Actions CI workflow.
- Added release runbook.
- Fixed frontend owner PDF button wiring.
- Fixed API version response to 0.23.0.

# Changelog

## 0.23.0
- Добавлен PDF-паспорт владельца.
- Добавлен публичный PDF по временной ссылке.
- Добавлен QR-код публичной ссылки.
- Добавлен административный backup SQLite + storage.
- Добавлена проверка backup manifest и SHA-256.
- Добавлен restore smoke test.

## 0.24.0

- Усилен `app.backup.verify_backup`.
- Добавлен безопасный restore без `extractall` в целевую директорию до проверки.
- Добавлен `scripts/restore_backup.py`.
- Добавлен endpoint `/api/admin/backups/{backup_name}/restore-check`.
- Добавлены тесты на tampering, path traversal и непустую директорию восстановления.
- Admin token сравнивается через `hmac.compare_digest`.
- Restore smoke test теперь поднимает приложение поверх восстановленной SQLite-базы и проверяет `/ready`.
