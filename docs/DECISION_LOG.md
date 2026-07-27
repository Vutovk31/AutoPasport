# Decision Log

## ADR-068 — GitHub is the canonical source

После ручной загрузки исходников разработка продолжается от ветки `main`, а ZIP-архивы используются как release snapshots и резервные артефакты.

## ADR-069 — Repository integrity is a release gate

Структурная полнота репозитория проверяется до миграций и функциональных тестов. Отсутствие обязательного файла блокирует release verification.

## ADR-070 — Production configuration fails closed

При `APP_ENV=production` AutoPassport не запускается с небезопасными параметрами. Проверка выполняется отдельной командой до Alembic migrations и FastAPI, чтобы ошибка конфигурации не маскировалась частично запущенным приложением.

## ADR-071 — Development remains low-friction

Строгие требования HTTPS, secure cookie и сильного admin token обязательны только для production. Development и test сохраняют локальный HTTP-сценарий, но проходят общую проверку URL, каталогов и размера загрузки.

## ADR-072 — Public repository privacy fails closed

Публичный GitHub рассматривается как недоверенная граница публикации. CI должен остановиться до миграций и тестов, если обнаружены приватные runtime-файлы, credential containers, известные форматы секретов или возможный реальный VIN вне узкого allowlist синтетических шаблонов.

## ADR-073 — Privacy allowlist is explicit and minimal

Исключения для VIN-проверки разрешаются только по точному пути для тестовых и шаблонных данных. Общие каталоги и произвольные файлы не исключаются из проверки.

## ADR-074 — Storage quota is owner-wide

Квота считается по всем активным вложениям всех автомобилей владельца, а не по одному событию, визиту или автомобилю. Это исключает обход лимита созданием дополнительных автомобилей или распределением документов между двумя типами истории.

## ADR-075 — Soft-deleted attachments release quota

В MVP квоту потребляют только активные вложения. Soft-deleted записи не учитываются, поскольку недоступны владельцу как действующие доказательства; физическое удаление файла и политика retention остаются отдельным production-блоком.

## ADR-076 — Storage enforcement and usage share one calculation

Listener, backend read service и API обязаны использовать `storage_usage_for_owner`. Отдельные SQL-запросы для отображения usage запрещены, поскольку создают риск расхождения лимитов, остатка и фактического enforcement.

## ADR-077 — Usage percentages are derived server-side

Backend возвращает проценты использования по количеству вложений и байтам вместе с абсолютными значениями. Это закрепляет единое округление и исключает различия между web/PWA-клиентами.

## ADR-078 — Storage usage endpoint is authenticated owner scope

`GET /api/me/storage` использует `current_user` и возвращает только суммарное использование текущего владельца. Идентификатор владельца не принимается из URL или query-параметров, чтобы исключить горизонтальный доступ к чужой статистике.

## ADR-079 — FastAPI main module is a composition root

Существующие маршруты сохранены в `app/application.py`, а `app/main.py` отвечает за сборку приложения и подключение новых поперечных API. Это временно снижает риск дальнейшего роста монолитного файла без изменения внешней точки запуска `uvicorn app.main:app`.

## ADR-080 — Owner UI renders server storage usage without recalculation

Web/PWA-клиент отображает абсолютные значения, остатки и проценты из `GET /api/me/storage`. Клиент не воспроизводит формулу квоты, чтобы интерфейс не расходился с backend enforcement.

## ADR-081 — Storage warnings use fixed MVP thresholds

Для MVP предупреждение показывается при достижении 80% любой квоты, критическое состояние — при 95%. Порог определяется максимальным из процентов количества и объёма; тарифные или пользовательские пороги отложены за пределы MVP.

## ADR-082 — Active public-link limits are owner-wide and per vehicle

Публичные ссылки ограничиваются одновременно на уровне автомобиля и владельца. Это исключает обход owner-wide лимита распределением ссылок по множеству автомобилей и сохраняет простой сценарий одной актуальной ссылки на автомобиль.

## ADR-083 — Expired and revoked links do not consume quota

Квота учитывает только ссылки без `revoked_at` и с `expires_at` позже текущего времени. Исторические записи остаются в базе для аудита, но не блокируют создание новой временной ссылки.

## ADR-084 — Public share usage is visible before mutation

Owner UI показывает активные ссылки, общий лимит и остаток через `GET /api/me/shares` до создания новой ссылки. Пользователь не должен узнавать о лимите только из отказа mutation endpoint.

## ADR-085 — Share usage refreshes after every create attempt

После успешной и неуспешной попытки создания ссылки frontend повторно загружает owner-wide usage. Это устраняет расхождение карточки с backend после автоматического отзыва предыдущей ссылки или quota error; отдельный realtime-канал для MVP не вводится.

## ADR-086 — Active share list never returns public tokens

`GET /api/me/shares/list` возвращает идентификатор записи, автомобиль и временные метаданные, но не исходный token и не публичный URL. Token хранится только в виде hash, поэтому существующая публичная ссылка не может быть восстановлена из базы или owner list.

## ADR-087 — Revoke reuses the existing ownership-checked mutation

Owner UI отзывает ссылку через существующий `DELETE /api/share/{share_id}`. Новый параллельный revoke endpoint не создаётся: текущий маршрут уже требует mutation guard, CSRF token и проверяет принадлежность автомобиля текущему владельцу.

## ADR-088 — Attachment retention is CLI-only and dry-run first

Физическое удаление доказательств не предоставляется через HTTP API и не запускается автоматически при старте приложения. Оператор сначала выполняет `scripts/cleanup_attachments.py` без `--apply`, изучает JSON report и при необходимости создаёт backup. Это уменьшает риск случайной массовой очистки из owner UI, внешнего запроса или restart-контейнера.

## ADR-089 — Retention cleanup fails closed on integrity anomalies

Apply не выполняет частичную очистку, если найден пропавший активный файл, symlink, небезопасный путь, soft-deleted запись без `deleted_at` или физический файл для записи, уже отмеченной как purged. Активные файлы защищаются независимо от возраста. Удаляются только повторно проверенные старые soft-deleted файлы и старые orphan-файлы; результат физического удаления фиксируется в SQLite и атомарном JSON audit report.

## ADR-090 — Release verification is one auditable operation

Release candidate проверяется командой `scripts/release_check.py`, которая запускает privacy, runtime configuration, Alembic head, compilation, полный pytest, restore CLI, retention CLI и Docker Compose для одного checkout. Отдельные частичные проверки не являются основанием для повышения версии.

## ADR-091 — Failed CI must still publish its report

GitHub Actions сохраняет JSON release report через `if: always()`. Отчёт должен быть доступен и при падении, иначе невозможно отличить дефект тестов от отсутствия observability. `VERSION` повышается только после успешного отчёта без `failed_steps`.