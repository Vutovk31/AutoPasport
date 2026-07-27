# AutoPassport v0.24.1

Каноническая MVP-сборка электронного паспорта автомобиля: ремонтные визиты, позиции работ и деталей, trust-модель, временный публичный паспорт, PDF-отчёт, PWA и backup SQLite + storage.

## Статус репозитория

GitHub является каноническим источником исходного кода. Workflow `Repository integrity` проверяет наличие обязательных каталогов и файлов на каждом push и pull request.

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

## Backup и restore

Backup включает SQLite-базу, storage-файлы и `manifest.json` с SHA-256.

```bash
python scripts/restore_backup.py data/backups/<backup>.zip data/restored
python scripts/restore_backup.py data/backups/<backup>.zip data/restored --verify-only
```

Restore проверяет пути архива, SHA-256 базы и storage, SQLite integrity и наличие обязательных таблиц.

## PWA

Service worker кеширует только оболочку приложения. API, PDF и приватные данные остаются network-only.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

## CI

GitHub Actions проверяет целостность структуры, согласованность версии, миграции, компиляцию Python, pytest и синтаксис Docker Compose.
