# TODO

## Критично

- Получить зелёный результат основного CI после добавления configuration, repository privacy, storage quota, storage UI, public share gates и attachment retention.
- Проверить production-пример конфигурации на реальном deployment target.
- Сохранять allowlist privacy gate только для синтетических тестовых VIN и шаблонов; реальные данные не коммитить.
- Перед первым production cleanup выполнить dry-run и сохранить JSON audit report вместе с backup.

## Следующий функциональный блок

- Реализовать retention cleanup истёкших и отозванных ShareLink после установленного периода аудита.
- Добавить maintenance runner, который запускает cleanup-команды отдельно от application startup.
- Подтвердить, что backup после attachment cleanup не содержит physically purged файлов, а SQLite сохраняет purge audit metadata.

## После MVP security baseline

- Полноценная административная роль вместо статического токена.
- Внешний backup storage.
- Production HTTPS deployment и мониторинг ошибок.
- Транзакционная защита quota при многопроцессном deployment.
