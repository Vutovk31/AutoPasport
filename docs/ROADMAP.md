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

## Следующий приоритет

- Подтвердить зелёный release-check версии `0.25.0` после merge в `main`.
- Зафиксировать итоговый commit SHA и SHA-256 release artifact как доказательство первого MVP-релиза.
- Выполнить controlled local/Docker smoke test: регистрация → автомобиль → визит → вложение → публичная ссылка → PDF → backup/restore.
- После завершения release freeze перейти к retention cleanup исторических истёкших ShareLink и maintenance runner.
