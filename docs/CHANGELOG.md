# Changelog

## Unreleased

- Добавлен `app/config.py` с типизированной runtime-конфигурацией.
- Добавлен production startup gate: HTTPS, secure cookie, сильный admin token, безопасный DATABASE_URL и раздельные storage/backup paths.
- Добавлена команда `python scripts/check_config.py`.
- Docker entrypoint теперь проверяет конфигурацию до миграций и запуска приложения.
- Добавлены тесты production configuration gate.
- Основной CI проверяет runtime-конфигурацию перед миграциями.
- Добавлен `scripts/check_repository_privacy.py` для защиты публичного репозитория от приватных файлов, credential containers, секретов и возможных реальных VIN.
- Добавлены тесты privacy gate.
- Основной CI выполняет privacy gate до миграций и функциональных тестов.
- Добавлен owner-wide storage quota для активных вложений событий и сервисных визитов.
- Добавлены лимиты `MAX_OWNER_ATTACHMENTS` и `MAX_OWNER_STORAGE_BYTES`.
- Превышение количества вложений возвращает `owner_attachment_quota_exceeded` с HTTP 409.
- Превышение суммарного объёма возвращает `owner_storage_quota_exceeded` с HTTP 413.
- Добавлены тесты количества, объёма, soft-delete и невозможности определить владельца вложения.
- Добавлен переиспользуемый сервис `owner_storage_usage` для расчёта текущего использования и остатка квоты.
- Usage payload дополнен процентами использования по количеству вложений и байтам.
- Добавлены тесты владельца с файлами и владельца без автомобилей.

## 0.24.1

- Добавлен GitHub Actions workflow `Repository integrity`.
- Добавлена проверка обязательных файлов приложения.
- Добавлена проверка согласованности VERSION и README.
- GitHub закреплён как канонический источник исходного кода.
