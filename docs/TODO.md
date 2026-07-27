# TODO

## Критично

- Получить зелёный результат основного CI после добавления configuration, repository privacy, storage quota, storage UI и public share gates.
- Проверить production-пример конфигурации на реальном deployment target.
- Сохранять allowlist privacy gate только для синтетических тестовых VIN и шаблонов; реальные данные не коммитить.

## Следующий функциональный блок

- Реализовать retention cleanup физически удалённых вложений с dry-run и audit output.
- Удалять только файлы, которые soft-deleted дольше установленного периода и больше не входят в активную историю.
- Добавить тесты безопасного отказа при несоответствии database/storage.

## После MVP security baseline

- Полноценная административная роль вместо статического токена.
- Внешний backup storage.
- Production HTTPS deployment и мониторинг ошибок.
- Retention cleanup исторических истёкших ShareLink после периода аудита.