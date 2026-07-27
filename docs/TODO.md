# TODO

## Критично

- Получить зелёный результат основного CI после добавления configuration, repository privacy, storage quota, storage UI и public share gates.
- Проверить production-пример конфигурации на реальном deployment target.
- Сохранять allowlist privacy gate только для синтетических тестовых VIN и шаблонов; реальные данные не коммитить.

## Следующий функциональный блок

- Показать количество активных публичных ссылок и остаток лимита в owner UI.
- Обновлять share usage после создания, отзыва и истечения ссылки.
- Добавить браузерный сценарий создания и отзыва публичной ссылки.

## После MVP security baseline

- Полноценная административная роль вместо статического токена.
- Внешний backup storage.
- Production HTTPS deployment и мониторинг ошибок.
- Retention cleanup физически удалённых вложений.
