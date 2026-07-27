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
- Добавлен аутентифицированный endpoint `GET /api/me/storage`.
- `app/main.py` превращён в composition root, а существующие маршруты перенесены без изменения в `app/application.py`.
- Добавлены тесты авторизации, payload-контракта и OpenAPI для storage usage API.
- Добавлен owner UI с количеством документов, использованным объёмом, остатками и progress-индикаторами.
- Добавлены предупреждения при 80% и критическое состояние при 95% использования квоты.
- Добавлена расшифровка quota error codes в понятные сообщения.
- Восстановлен полный каталог `app/static`, включая PWA manifest, offline shell, service worker и иконки.
- Добавлены статические тесты storage UI и размещения PWA-артефактов.
- Добавлены owner-wide и per-vehicle лимиты активных публичных ссылок.
- Активные ссылки считаются только до истечения срока и до отзыва.
- Добавлен аутентифицированный endpoint `GET /api/me/shares`.
- Добавлены структурированные ошибки `vehicle_share_link_quota_exceeded` и `owner_share_link_quota_exceeded` с HTTP 409.
- Добавлены тесты usage, истечения, отзыва, авторизации и vehicle limit.
- Добавлена owner UI-карточка активных публичных ссылок с количеством, остатком и progress-индикатором.
- Share usage обновляется после входа, вручную и после каждой попытки создания ссылки.
- Quota errors публичных ссылок преобразуются в понятные владельцу сообщения.
- Добавлены статические тесты share usage UI и обновления после успешной/неуспешной попытки создания ссылки.

## 0.24.1

- Добавлен GitHub Actions workflow `Repository integrity`.
- Добавлена проверка обязательных файлов приложения.
- Добавлена проверка согласованности VERSION и README.
- GitHub закреплён как канонический источник исходного кода.