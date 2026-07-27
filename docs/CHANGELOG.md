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

## 0.24.1

- Добавлен GitHub Actions workflow `Repository integrity`.
- Добавлена проверка обязательных файлов приложения.
- Добавлена проверка согласованности VERSION и README.
- GitHub закреплён как канонический источник исходного кода.