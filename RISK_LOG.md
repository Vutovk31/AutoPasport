# Risk Log

- Нет антивирусного сканирования документов.
- Нет квот storage на владельца.
- Backup защищён статическим admin token; для production нужен полноценный admin role.
- PDF визуально достаточен для MVP, но требует дизайнерской полировки.
- Restore smoke test проверяет структуру архива, а не полноценный запуск восстановленного приложения.


## PWA / release risks
- Offline shell is intentionally limited: private vehicle data is not cached.
- Docker smoke is validated by compose configuration, not by a full remote deployment.
- GitHub Actions file is present and syntactically structured, but the workflow must be confirmed inside GitHub after manual repository upload.

- Current execution environment has no Docker binary; Docker Compose was statically checked by file-contract tests, while full compose validation is delegated to GitHub Actions or a local machine with Docker installed.

## v0.24.0

- Backup пока локальный; для production нужен внешний storage.
- Backup ZIP не шифруется.
- Restore-check не заменяет production volumes автоматически; это осознанно безопаснее для MVP.
