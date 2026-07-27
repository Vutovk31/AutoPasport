# TODO

## Критично

- Получить зелёный результат основного CI после добавления configuration, repository privacy и storage quota gates.
- Проверить production-пример конфигурации на реальном deployment target.
- Сохранять allowlist privacy gate только для синтетических тестовых VIN и шаблонов; реальные данные не коммитить.

## Следующий функциональный блок

- Добавить frontend-индикатор количества, байтов, остатка и процентов использования через `GET /api/me/storage`.
- Ограничить активные публичные ссылки.
- Отображать структурированные quota-ошибки во frontend.

## После MVP security baseline

- Полноценная административная роль вместо статического токена.
- Внешний backup storage.
- Production HTTPS deployment и мониторинг ошибок.
