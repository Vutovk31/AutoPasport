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

## Следующий приоритет

- Подтвердить зелёный основной CI после frontend, storage и share-link hardening.
- Подключить usage публичных ссылок к owner UI.
- Добавить очистку физически удалённых вложений по retention policy.
- После этого перейти к полноценной административной роли вместо статического токена.
