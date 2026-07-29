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

Проверка выполняется до миграций и тестов. Публичный репозиторий не должен содержать `.env`, рабочую SQLite-базу, приватные vehicle-файлы, ключи, токены или строки, соответствующие VIN-паттерну. Test/seed fixtures используют явно демонстрационные идентификаторы, поэтому path allowlist для VIN отсутствует.

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

## Public share limit boundary

```text
new ShareLink
→ resolve vehicle owner
→ count active, unrevoked and unexpired links
→ enforce per-vehicle limit
→ enforce owner-wide limit
→ insert or fail with structured HTTP 409
```

Активной считается только ссылка без `revoked_at` и с `expires_at` позже текущего времени. Enforcement выполняется на SQLAlchemy `before_insert`, поэтому защищает все пути создания ссылок. `GET /api/me/shares` использует тот же owner scope и показывает фактическое количество активных ссылок и остаток лимита.

## Public share owner UI boundary

```text
owner session restored
→ GET /api/me/shares
→ render active / maximum / remaining
→ warn at 80%
→ critical state at 100%
→ refresh after every create attempt and manual request
```

Frontend рассчитывает только процент для progress-индикатора из серверных абсолютных значений; лимиты и остаток не воспроизводятся на клиенте. Structured error codes `vehicle_share_link_quota_exceeded` и `owner_share_link_quota_exceeded` преобразуются в понятные сообщения, после чего usage перечитывается независимо от успеха создания ссылки.

## Active public share management boundary

```text
authenticated GET /api/me/shares/list
→ current_user
→ active_share_links(session, owner_id)
→ join ShareLink with owned Vehicle
→ exclude revoked and expired links
→ return vehicle identity, expires_at and seconds_remaining
→ owner UI revoke action
→ DELETE /api/share/{share_id}
→ ownership check through vehicle
→ refresh list and usage
```

Токен публичной ссылки не возвращается списковым endpoint: владелец получает только идентификатор записи, автомобиль и срок действия. Отзыв использует существующий mutation endpoint с CSRF-защитой и повторной owner-проверкой.

## Attachment retention boundary

```text
scripts/cleanup_attachments.py
→ dry-run by default
→ compare Attachment rows with STORAGE_PATH
→ protect every active attachment
→ report active missing files and unsafe paths
→ stop apply mode when integrity issues exist
→ select old soft-deleted files and old orphans
→ re-check eligibility immediately before unlink
→ physically delete
→ mark Attachment.purged_at / purge_reason
→ write atomic JSON audit report
```

Период задаётся `ATTACHMENT_RETENTION_DAYS`. Автоматический cleanup при старте приложения запрещён: операция запускается отдельно, сначала в dry-run. Пропавший активный файл, symlink, небезопасный `stored_name`, soft-delete без `deleted_at` или повторное появление уже purged-файла блокируют применение целиком. Историческая строка Attachment сохраняется в SQLite, а физическое удаление фиксируется полями `purged_at` и `purge_reason`.

## Release verification boundary

```text
workflow checkout
→ create bootstrap release-check.json
→ setup Python and install dependencies
→ scripts/release_check.py replaces bootstrap report
→ repository privacy
→ runtime configuration
→ Alembic head
→ Python compilation
→ complete pytest suite
→ restore and retention CLI imports
→ Docker Compose validation
→ final JSON release report
→ explicit commit status autopassport/release-check
→ artifact retained for inspection with if: always()
```

Release candidate принимается только при успешном завершении всех шагов одного запуска. Проверки не останавливаются после первой ошибки, поэтому итоговый JSON-отчёт содержит полный список дефектов. До запуска orchestrator workflow создаёт bootstrap-report со статусом `passed=false`. Если setup Python, установка зависимостей или сам runner завершаются раньше финальной записи, artifact всё равно содержит диагностируемый признак `workflow_before_release_runner`, а не отсутствующий файл.

Каждый шаг release runner имеет явный timeout. Отсутствующая executable, системная ошибка запуска или превышение timeout преобразуются в ordinary failed result с кодом 127 или 124, а не прерывают orchestrator исключением. Полноценный runner атомарно заменяет bootstrap-report после начала проверки.

GitHub Actions check runs и legacy commit statuses являются разными каналами наблюдаемости. Workflow поэтому явно публикует status context `autopassport/release-check` со значением `success` только при `passed=true` и пустом `failed_steps`; во всех остальных случаях публикуется `failure` со ссылкой на конкретный workflow run. Это делает результат доступным через Commit Status API и не заменяет JSON artifact как источник детальной диагностики.

## Release version boundary

```text
VERSION
→ app/main.py APP_VERSION
→ FastAPI app.version
→ GET /health
→ release tests
→ README / changelog
→ PWA cache generation identifier
```

`VERSION` является каноническим номером релиза. Composition root читает его при импорте, блокирует пустое значение, задаёт OpenAPI metadata и заменяет legacy `/health` route единым endpoint с тем же номером. Релизный тест требует совпадения runtime response, FastAPI metadata и файла `VERSION`; PWA cache identifier меняется при выпуске, чтобы установленный клиент получил новый application shell.

## Scan vehicle context boundary

```text
owner selects vehicle in garage
→ frontend stores vehicleId from an owned `/api/vehicles` row
→ scan screen renders make/model + masked VIN + mileage
→ upload action is enabled
→ POST /api/vehicles/{vehicleId}/documents
→ backend repeats owner/vehicle boundary check
```

Без выбранного автомобиля кнопка загрузки отключена. Смена автомобиля возвращает пользователя в гараж и восстанавливает фокус на активной карточке. Клиентский контекст уменьшает вероятность ошибки выбора, но не заменяет серверную проверку принадлежности автомобиля.
