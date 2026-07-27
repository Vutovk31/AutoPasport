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

## Public repository privacy boundary

```text
push / pull request
→ scripts/check_repository_privacy.py
→ required paths
→ forbidden private files and credential containers
→ secret-pattern scan
→ possible real VIN scan
→ runtime configuration and tests
```

Проверка выполняется до миграций и тестов. Публичный репозиторий не должен содержать `.env`, рабочую SQLite-базу, приватные vehicle-файлы, ключи, токены или реальный VIN вне явно разрешённых синтетических шаблонов.