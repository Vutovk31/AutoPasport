# Decision Log

## ADR-068 — GitHub is the canonical source

После ручной загрузки исходников разработка продолжается от ветки `main`, а ZIP-архивы используются как release snapshots и резервные артефакты.

## ADR-069 — Repository integrity is a release gate

Структурная полнота репозитория проверяется до миграций и функциональных тестов. Отсутствие обязательного файла блокирует release verification.
