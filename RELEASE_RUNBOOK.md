# Release Runbook 0.24.0

## Local release smoke

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
pytest -q
uvicorn app.main:app --reload
```

## Docker release smoke

```bash
cp .env.example .env
docker compose up --build
```

Open:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/ready
http://127.0.0.1:8000/manifest.webmanifest
```

## Release boundary

- Full VIN and госномер are never committed to public seed files.
- Service worker must not cache `/api/*`, PDFs, storage files or private payloads.
- Backup must include SQLite and storage files together.


## Restore smoke

```bash
python scripts/restore_backup.py data/backups/<backup>.zip /tmp/autopassport-restore --verify-only
python scripts/restore_backup.py data/backups/<backup>.zip /tmp/autopassport-restore --overwrite
```

The restore target must not be a production volume unless the operator intentionally performs a recovery procedure.
