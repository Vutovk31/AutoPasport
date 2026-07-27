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

## Следующий приоритет

- Получить первый явный commit status нового workflow и определить `success` либо первый подтверждённый failed step.
- При failure получить JSON artifact и исправить фактические `failed_steps` до полностью зелёного результата.
- После подтверждения повысить `VERSION` до `0.25.0` и сформировать release snapshot.
- Затем реализовать retention cleanup исторических истёкших ShareLink после периода аудита.
