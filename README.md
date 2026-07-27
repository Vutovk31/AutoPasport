# AutoPassport v0.23.0

Каноническая MVP-сборка с ремонтными визитами, позициями работ, динамической trust-моделью, временным публичным паспортом, PDF-отчётом и backup SQLite + storage.

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


## PWA

AutoPassport 0.23.0 includes an installable PWA shell:

```text
/manifest.webmanifest
/service-worker.js
/offline.html
/static/icons/icon-192.png
/static/icons/icon-512.png
```

The service worker caches only the application shell. API responses, PDFs and private vehicle data are intentionally network-only.

## Docker release run

```bash
cp .env.example .env
docker compose up --build
```

The container applies Alembic migrations on startup and exposes the app at http://127.0.0.1:8000.

## CI

GitHub Actions runs migrations, compiles Python modules, executes pytest and validates docker-compose syntax.

## Verification note

`pytest -q` does not require Docker. Docker Compose validation requires Docker to be installed locally or in CI.


## Restore hardening

```bash
python scripts/restore_backup.py data/backups/<backup>.zip data/restored
python scripts/restore_backup.py data/backups/<backup>.zip data/restored --verify-only
```

Restore checks archive paths, database SHA-256, storage SHA-256, SQLite integrity and required schema tables.
