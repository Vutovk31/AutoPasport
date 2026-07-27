# Architecture

## Repository integrity boundary

```text
push / pull request
→ checkout
→ verify required project artifacts
→ verify VERSION ↔ README
→ continue to migrations, compile and tests
```

Релиз не считается проверяемым, если отсутствует хотя бы один обязательный компонент приложения.

## Runtime configuration boundary

```text
container / local startup
→ scripts/check_config.py
→ app.config.load_runtime_config
→ production safety rules
→ Alembic migrations
→ FastAPI process
```

При `APP_ENV=production` запуск блокируется без HTTPS, secure cookie, сильного admin token, безопасного DATABASE_URL и раздельных каталогов storage/backup. Проверка выполняется до миграций, чтобы приложение не стартовало с заведомо небезопасной конфигурацией.
