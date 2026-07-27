# TODO

## Критично

- Подтвердить `autopassport/release-check = success` для merge commit версии `0.25.0` в `main`.
- Скачать итоговый JSON artifact и зафиксировать `passed=true`, пустой `failed_steps`, commit SHA и SHA-256 artifact.
- Выполнить smoke test на реальном deployment target: регистрация → автомобиль → сервисный визит → документ → публичная ссылка → PDF → backup/restore.
- Проверить production-пример конфигурации на выбранном deployment target.
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
