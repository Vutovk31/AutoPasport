# Architecture 0.23.0

```text
Owner UI
→ FastAPI
→ SQLAlchemy
→ Alembic
→ SQLite
→ filesystem storage
```

## PDF

PDF строится из того же payload, что публичный паспорт. Приватный отчёт владельца использует полный VIN, публичный — только маскированный VIN.

## Backup

Backup — zip-архив:

```text
database/autopassport.db
storage/*
manifest.json
```

Manifest хранит SHA-256 storage-файлов. Restore выполняется только после verify.

## Backup / Restore boundary v0.24.0

```text
backup.zip
→ safe archive path validation
→ manifest validation
→ database SHA-256
→ storage SHA-256
→ SQLite PRAGMA integrity_check
→ required schema tables
→ staging extract
→ target replacement
```

Backup-архив считается недоверенным вводом даже для администратора.
