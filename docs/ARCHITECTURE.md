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

## Owner storage quota boundary

```text
new Attachment
→ resolve owner through HistoryEvent or ServiceVisit
→ storage_usage_for_owner
→ collect active attachments across all owner vehicles
→ check MAX_OWNER_ATTACHMENTS
→ check projected MAX_OWNER_STORAGE_BYTES
→ insert or fail with structured HTTP error
```

Лимит применяется на уровне SQLAlchemy `before_insert`, поэтому одинаково защищает вложения старых событий и сервисных визитов. Soft-deleted вложения не потребляют квоту. Проверка выполняется до записи строки Attachment; физический файл удаляется существующим rollback-контуром upload endpoint при исключении.

## Storage usage API boundary

```text
authenticated GET /api/me/storage
→ current_user
→ owner_storage_usage(session, owner_id)
→ storage_usage_for_owner
→ active event + visit attachments across all vehicles
→ used / maximum / remaining / utilization percent
→ stable JSON payload
```

Расчёт квоты и API используют одну функцию `storage_usage_for_owner`, поэтому frontend видит те же значения, которыми backend блокирует новые загрузки. `app/main.py` является composition root; существующее приложение сохранено в `app/application.py`, а новые поперечные API подключаются без дальнейшего разрастания монолитного файла.

## Storage usage owner UI boundary

```text
owner session restored
→ GET /api/me/storage
→ render document and byte utilization
→ warn at 80%
→ critical warning at 95%
→ refresh after deletion and manual request
```

Frontend не вычисляет лимиты самостоятельно: он отображает серверный read model. Коды `owner_attachment_quota_exceeded` и `owner_storage_quota_exceeded` преобразуются в понятные владельцу сообщения. Приватные ответы API не кешируются service worker.