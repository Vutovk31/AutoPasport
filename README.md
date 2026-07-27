# AutoPassport v0.24.0

Каноническая MVP-сборка электронного паспорта автомобиля с ремонтными визитами, позициями работ и деталей, trust-моделью, временным публичным паспортом, PDF-отчётом, PWA и backup/restore SQLite + storage.

## Статус репозитория

GitHub содержит каноническую структуру проекта:

```text
app/
alembic/
scripts/
tests/
docs/
.github/workflows/
```

Рабочими считаются только файлы внутри канонических директорий. Текущие изменения после v0.24.0 ведутся в секции `Unreleased` до подтверждённого зелёного CI и следующего релизного тега.

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

Фактическое число пройденных тестов фиксируется CI для конкретного commit SHA; README не закрепляет устаревающее статическое число.

## Owner storage usage

После входа интерфейс запрашивает:

```http
GET /api/me/storage
```

Owner UI показывает количество документов, использованный объём, остаток квоты и предупреждения при 80%/95%. Backend и frontend используют один серверный read model; структурированные quota errors преобразуются в понятные сообщения.

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

Service worker кеширует только application shell. API responses, PDF и приватные данные автомобиля намеренно остаются network-only.

## Docker release run

```bash
cp .env.example .env
docker compose up --build
```

Контейнер применяет Alembic migrations на старте и поднимает приложение на `http://127.0.0.1:8000`.

## CI

GitHub Actions проверяет repository privacy, runtime configuration, migrations, Python compilation, pytest, restore CLI и Docker Compose configuration.