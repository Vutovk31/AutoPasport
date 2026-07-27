# Changelog

## Unreleased

- Новые изменения после первого подтверждённого MVP-релиза ещё не добавлены.

## 0.25.0 — 2026-07-28

- Добавлен `app/config.py` с типизированной runtime-конфигурацией.
- Добавлен production startup gate: HTTPS, secure cookie, сильный admin token, безопасный DATABASE_URL и раздельные storage/backup paths.
- Добавлена команда `python scripts/check_config.py`.
- Docker entrypoint теперь проверяет конфигурацию до миграций и запуска приложения.
- Добавлены тесты production configuration gate.
- Основной CI проверяет runtime-конфигурацию перед миграциями.
- Добавлен `scripts/check_repository_privacy.py` для защиты публичного репозитория от приватных файлов, credential containers, секретов и возможных реальных VIN.
- Добавлены тесты privacy gate.
- Основной CI выполняет privacy gate до миграций и функциональных тестов.
- Добавлен owner-wide storage quota для активных вложений событий и сервисных визитов.
- Добавлены лимиты `MAX_OWNER_ATTACHMENTS` и `MAX_OWNER_STORAGE_BYTES`.
- Превышение количества вложений возвращает `owner_attachment_quota_exceeded` с HTTP 409.
- Превышение суммарного объёма возвращает `owner_storage_quota_exceeded` с HTTP 413.
- Добавлены тесты количества, объёма, soft-delete и невозможности определить владельца вложения.
- Добавлен переиспользуемый сервис `owner_storage_usage` для расчёта текущего использования и остатка квоты.
- Usage payload дополнен процентами использования по количеству вложений и байтам.
- Добавлены тесты владельца с файлами и владельца без автомобилей.
- Добавлен аутентифицированный endpoint `GET /api/me/storage`.
- `app/main.py` превращён в composition root, а существующие маршруты перенесены без изменения в `app/application.py`.
- Добавлены тесты авторизации, payload-контракта и OpenAPI для storage usage API.
- Добавлен owner UI с количеством документов, использованным объёмом, остатками и progress-индикаторами.
- Добавлены предупреждения при 80% и критическое состояние при 95% использования квоты.
- Добавлена расшифровка quota error codes в понятные сообщения.
- Восстановлен полный каталог `app/static`, включая PWA manifest, offline shell, service worker и иконки.
- Добавлены статические тесты storage UI и размещения PWA-артефактов.
- Добавлены owner-wide и per-vehicle лимиты активных публичных ссылок.
- Активные ссылки считаются только до истечения срока и до отзыва.
- Добавлен аутентифицированный endpoint `GET /api/me/shares`.
- Добавлены структурированные ошибки `vehicle_share_link_quota_exceeded` и `owner_share_link_quota_exceeded` с HTTP 409.
- Добавлены тесты usage, истечения, отзыва, авторизации и vehicle limit.
- Добавлена owner UI-карточка активных публичных ссылок с количеством, остатком и progress-индикатором.
- Share usage обновляется после входа, вручную и после каждой попытки создания ссылки.
- Quota errors публичных ссылок преобразуются в понятные владельцу сообщения.
- Добавлены статические тесты share usage UI и обновления после успешной/неуспешной попытки создания ссылки.
- Добавлен `GET /api/me/shares/list` с owner-scoped списком действующих ссылок, автомобилем, сроком действия и оставшимся временем.
- Owner UI показывает конкретные активные ссылки и позволяет отозвать их через существующий `DELETE /api/share/{share_id}`.
- После отзыва список и агрегированное usage обновляются одним frontend-сценарием.
- Добавлены тесты read model, маршрутов и revoke UI.
- Добавлен `app/attachment_retention.py` для сверки SQLite и physical storage.
- Добавлен CLI `python scripts/cleanup_attachments.py`; dry-run используется по умолчанию, физическое удаление требует `--apply`.
- Добавлена миграция `0003_attachment_retention` с полями `purged_at` и `purge_reason`.
- Cleanup блокирует apply при пропавшем активном файле, небезопасном пути, symlink или неконсистентном soft-delete.
- Старые soft-deleted файлы и старые orphan-файлы удаляются только после повторной проверки непосредственно перед unlink.
- Каждый запуск формирует атомарный JSON audit report в `data/reports`.
- Добавлены тесты dry-run, apply, защиты активного файла, orphan cleanup, missing active file и audit report.
- Добавлен `scripts/release_check.py`, объединяющий privacy, config, migrations, compilation, полный pytest, maintenance CLI и Docker Compose validation.
- Release check формирует JSON-отчёт со всеми шагами и не скрывает дополнительные ошибки после первого сбоя.
- GitHub Actions всегда публикует `autopassport-release-check` как artifact, включая неуспешные сборки.
- Добавлены тесты состава release suite, skip-docker режима, агрегации ошибок и JSON report.
- Release runner преобразует отсутствующую executable и системную ошибку запуска в failed step с кодом 127.
- Для каждого release step добавлен явный timeout; превышение фиксируется кодом 124 с сохранением доступного stdout/stderr.
- Добавлены тесты продолжения release-check после отсутствующей команды, timeout diagnostics и передачи лимита времени runner-у.
- CI создаёт bootstrap `release-check.json` до setup Python и установки зависимостей, поэтому artifact сохраняется даже при раннем падении workflow.
- Добавлен ручной запуск `workflow_dispatch` для повторяемой release verification без нового commit.
- Добавлены статические тесты порядка bootstrap/install/release и обязательной публикации artifact через `if: always()`.
- Workflow получил явные разрешения `contents: read` и `statuses: write`.
- После каждого запуска публикуется commit status `autopassport/release-check`: `success` только при `passed=true` и пустом `failed_steps`, иначе `failure` со ссылкой на workflow run.
- Добавлены тесты commit-status context, permissions, failure fallback и ограничения description.
- Добавлена автоприменяемая test-fixture, полностью очищающая кэш модулей `app.*` и закрывающая старый SQLAlchemy engine между тестами.
- Release-тесты синхронизированы с единым orchestrator `scripts/release_check.py` вместо устаревших прямых команд в workflow.
- Docker Compose больше не требует существования локального `.env` для структурной валидации и использует безопасные переменные с defaults.
- Публичные test/seed identifiers заменены на явно демонстрационные значения, а VIN privacy allowlist удалён.
- Исправлена runtime identity проверка `ShareQuotaExceeded` после изоляции модулей между тестами.
- Runtime `/health`, FastAPI OpenAPI metadata и PWA cache синхронизированы с каноническим `VERSION=0.25.0`.
- Для release candidate и итогового `main` подтверждены восемь из восьми release gates и полный набор из 70 тестов.

## 0.24.1

- Добавлен GitHub Actions workflow `Repository integrity`.
- Добавлена проверка обязательных файлов приложения.
- Добавлена проверка согласованности VERSION и README.
- GitHub закреплён как канонический источник исходного кода.
