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

## Следующий приоритет

- Показать storage usage в owner UI до загрузки файла.
- Подтвердить зелёный основной CI после security и quota hardening.
- Ограничить активные публичные ссылки и добавить явный статус лимита в API.
- После этого перейти к полноценной административной роли вместо статического токена.
