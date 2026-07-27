# AutoPassport v0.24.0

Каноническая MVP-сборка электронного паспорта автомобиля с ремонтными визитами, позициями работ и деталей, trust-моделью, временным публичным паспортом, PDF-отчётом, PWA и backup/restore SQLite + storage.

## Статус репозитория

GitHub теперь содержит восстановленную структуру ключевых директорий:

```text
app/
alembic/
scripts/
tests/
.github/workflows/
```

Корневые дубли Python-модулей, Alembic-файлов, shell-скриптов, тестов и CI workflow, появившиеся из-за ручной загрузки без папок, удалены. Рабочими считаются только файлы внутри канонических директорий.

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Открыть: `http://127.0.0.1:8000`

## Тесты

```bash
pytest -q
```

Ожидаемый результат канонической сборки v0.24.0:

```text
15 passed
```

## Backup

В `.env` задайте:

```text
ADMIN_BACKUP_TOKEN=change-me
BACKUP_PATH=./data/backups
```

Создать backup:

```bash
curl -X POST http://127.0.0.1:8000/api/admin/backups \
  -H 'X-Admin-Token: change-me'
```

Backup включает SQLite-базу, storage-файлы и `manifest.json` с SHA-256.

## Restore hardening

```bash
python scripts/restore_backup.py data/backups/<backup>.zip data/restored
python scripts/restore_backup.py data/backups/<backup>.zip data/restored --verify-only
```

Restore проверяет archive paths, database SHA-256, storage SHA-256, SQLite integrity и обязательные таблицы схемы.

## PWA

AutoPassport включает installable PWA shell:

```text
/manifest.webmanifest
/service-worker.js
/offline.html
/static/icons/icon-192.png
/static/icons/icon-512.png
```

Service worker кеширует только application shell. API responses, PDFs и приватные данные автомобиля намеренно остаются network-only.

## Docker release run

```bash
cp .env.example .env
docker compose up --build
```

Контейнер применяет Alembic migrations на старте и поднимает приложение на `http://127.0.0.1:8000`.

## CI

GitHub Actions должен запускать migrations, compile, pytest и docker-compose config validation.
