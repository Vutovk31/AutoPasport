# TODO

## Критично

- Проверить commit status context `autopassport/release-check` для актуального commit SHA.
- При `failure` получить JSON artifact `autopassport-release-check` и разобрать только фактические `failed_steps`.
- При `success` зафиксировать конкретный commit SHA как release candidate и только после этого повышать версию.
- Проверить production-пример конфигурации на реальном deployment target.
- Сохранять allowlist privacy gate только для синтетических тестовых VIN и шаблонов; реальные данные не коммитить.
- Перед первым production cleanup выполнить dry-run и сохранить JSON audit report вместе с backup.

## Следующий функциональный блок

- После зелёного release check повысить `VERSION` до `0.25.0` и сформировать release snapshot.
- Реализовать retention cleanup истёкших и отозванных ShareLink после установленного периода аудита.
- Добавить maintenance runner, который запускает cleanup-команды отдельно от application startup.
- Подтвердить, что backup после attachment cleanup не содержит physically purged файлов, а SQLite сохраняет purge audit metadata.

## После MVP security baseline

- Полноценная административная роль вместо статического токена.
- Внешний backup storage.
- Production HTTPS deployment и мониторинг ошибок.
- Транзакционная защита quota при многопроцессном deployment.
