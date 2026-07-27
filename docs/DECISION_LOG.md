# Decision Log

## ADR-068 — GitHub is the canonical source

После ручной загрузки исходников разработка продолжается от ветки `main`, а ZIP-архивы используются как release snapshots и резервные артефакты.

## ADR-069 — Repository integrity is a release gate

Структурная полнота репозитория проверяется до миграций и функциональных тестов. Отсутствие обязательного файла блокирует release verification.

## ADR-070 — Production configuration fails closed

При `APP_ENV=production` AutoPassport не запускается с небезопасными параметрами. Проверка выполняется отдельной командой до Alembic migrations и FastAPI, чтобы ошибка конфигурации не маскировалась частично запущенным приложением.

## ADR-071 — Development remains low-friction

Строгие требования HTTPS, secure cookie и сильного admin token обязательны только для production. Development и test сохраняют локальный HTTP-сценарий, но проходят общую проверку URL, каталогов и размера загрузки.
