# Roadmap

## Завершено

- GitHub назначен каноническим источником исходного кода.
- Добавлен обязательный repository integrity gate.
- Добавлена проверка согласованности VERSION и README.
- Добавлен runtime configuration gate до миграций и старта приложения.
- Зафиксированы обязательные production-настройки HTTPS, cookie, admin token, database и storage paths.
- Добавлен public repository privacy gate для приватных файлов, credential containers, секретов и возможных реальных VIN.
- Реализована owner-wide storage quota по количеству и суммарному объёму активных вложений.
- Реализован единый backend-сервис расчёта storage usage, остатка и процентов использования.
- Подключён аутентифицированный endpoint `GET /api/me/storage` с OpenAPI-контрактом.
- Storage usage подключён к owner UI с progress-индикаторами и предупреждениями 80%/95%.
- Восстановлена каноническая структура `app/static` и PWA shell.
- Ограничено число активных публичных ссылок на автомобиль и владельца.
- Добавлен аутентифицированный endpoint `GET /api/me/shares` и структурированные quota errors.
- Share usage подключён к owner UI с количеством, остатком, progress-индикатором и обновлением после попытки создания ссылки.
- Добавлен owner-scoped список активных публичных ссылок с автомобилем, сроком действия и оставшимся временем.
- Добавлен явный отзыв активной ссылки из owner UI с последующим обновлением списка и usage.
- Реализован attachment retention cleanup: dry-run, database/storage reconciliation, fail-closed integrity gate, физическое удаление старых soft-deleted и orphan-файлов, purge audit fields и JSON report.
- Добавлен единый release verification runner и обязательный JSON artifact GitHub Actions.
- Release runner защищён от отсутствующей executable, системных ошибок запуска и зависших команд; отчёт продолжает формироваться с кодами 127/124.
- CI создаёт bootstrap release report до установки зависимостей и поддерживает ручной `workflow_dispatch`.
- CI публикует явный commit status `autopassport/release-check`, доступный через Commit Status API независимо от обычных GitHub Actions check runs.
- Устранена утечка test application state между SQLite-базами и storage-каталогами.
- Удалён VIN privacy allowlist; публичные fixtures используют только демонстрационные идентификаторы.
- Получен первый полностью зелёный release-check на `main`: 8/8 gates и 70 тестов.
- Подготовлена релизная версия `0.25.0` с единым runtime, OpenAPI и PWA version metadata.
- На экране «Скан» добавлен явный контекст выбранного автомобиля с маскированным VIN, пробегом и безопасным возвратом в гараж.
- Загрузка документа блокируется до выбора автомобиля, поэтому файл нельзя случайно отправить в неопределённый паспорт.

## Следующий приоритет

- Восстановить зелёный полный `pytest`: текущий `HEAD` содержит 19 регрессий, существовавших до UX-итерации выбранного автомобиля.
- После зелёного тестового контура выполнить мобильный smoke test: два автомобиля → выбор второго → «Скан» → проверка имени/VIN → загрузка документа → проверка привязки.
- Затем подключить реальный parser worker к уже существующему безопасному жизненному циклу `uploaded → processing → needs_review/failed`.
