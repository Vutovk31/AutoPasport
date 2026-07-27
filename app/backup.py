from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile

from .database import database_url

BACKUP_DIR = Path(os.getenv('BACKUP_PATH', './data/backups')).resolve()
STORAGE_DIR = Path(os.getenv('STORAGE_PATH', './data/storage')).resolve()
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_TABLES = {'alembic_version', 'users', 'vehicles', 'service_visits'}


def _sqlite_path() -> Path:
    if not database_url.startswith('sqlite:///'):
        raise RuntimeError('Only sqlite backup is supported in MVP')
    raw = database_url.replace('sqlite:///', '', 1)
    return Path(raw).resolve()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_safe_archive_path(name: str) -> bool:
    try:
        path = PurePosixPath(name)
    except Exception:
        return False
    if path.is_absolute():
        return False
    return '..' not in path.parts and name not in ('', '.')


def _ensure_safe_archive(archive: zipfile.ZipFile) -> None:
    for item in archive.infolist():
        if not _is_safe_archive_path(item.filename):
            raise RuntimeError(f'Unsafe archive entry: {item.filename}')


def _safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    destination = destination.resolve()
    _ensure_safe_archive(archive)
    for item in archive.infolist():
        target = (destination / item.filename).resolve()
        if destination != target and destination not in target.parents:
            raise RuntimeError(f'Unsafe archive entry: {item.filename}')
    archive.extractall(destination)


def _validate_sqlite_bytes(raw: bytes) -> dict:
    with tempfile.TemporaryDirectory(prefix='autopassport-sqlite-check-') as temp:
        db_path = Path(temp) / 'autopassport.db'
        db_path.write_bytes(raw)
        try:
            with sqlite3.connect(db_path) as connection:
                integrity = connection.execute('PRAGMA integrity_check').fetchone()
                if not integrity or integrity[0] != 'ok':
                    return {'ok': False, 'reason': f'SQLite integrity check failed: {integrity}'}
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        except sqlite3.DatabaseError as exc:
            return {'ok': False, 'reason': f'Invalid SQLite database: {exc}'}
    missing = sorted(REQUIRED_TABLES - tables)
    if missing:
        return {'ok': False, 'reason': 'SQLite schema is incomplete: ' + ', '.join(missing)}
    return {'ok': True, 'tables': sorted(tables)}


def create_backup(version: str) -> dict:
    db_path = _sqlite_path()
    if not db_path.exists():
        raise FileNotFoundError(f'Database not found: {db_path}')
    created = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name = f'autopassport_backup_{version}_{created}.zip'
    target = BACKUP_DIR / name
    files = []
    db_sha = sha256_file(db_path)
    manifest = {
        'app': 'AutoPassport',
        'version': version,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'database': {
            'archive_path': 'database/autopassport.db',
            'sha256': db_sha,
            'size': db_path.stat().st_size,
        },
        'storage': [],
    }
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(db_path, 'database/autopassport.db')
        files.append('database/autopassport.db')
        if STORAGE_DIR.exists():
            for path in sorted(STORAGE_DIR.rglob('*')):
                if path.is_file() and path.name != '.gitkeep':
                    arc = 'storage/' + str(path.relative_to(STORAGE_DIR)).replace('\\', '/')
                    z.write(path, arc)
                    manifest['storage'].append({
                        'archive_path': arc,
                        'sha256': sha256_file(path),
                        'size': path.stat().st_size,
                    })
                    files.append(arc)
        z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    return {
        'name': name,
        'path': str(target),
        'size_bytes': target.stat().st_size,
        'sha256': sha256_file(target),
        'files': files,
    }


def verify_backup(path: str | Path) -> dict:
    backup = Path(path)
    if not backup.exists():
        raise FileNotFoundError(str(backup))
    try:
        with zipfile.ZipFile(backup) as z:
            _ensure_safe_archive(z)
            names = set(z.namelist())
            if 'manifest.json' not in names:
                return {'verified': False, 'reason': 'manifest is missing'}
            manifest = json.loads(z.read('manifest.json').decode('utf-8'))
            database = manifest.get('database') or {}
            db_arc = database.get('archive_path')
            if not db_arc or db_arc not in names:
                return {'verified': False, 'reason': 'database is missing'}
            if not _is_safe_archive_path(db_arc):
                return {'verified': False, 'reason': f'unsafe database path {db_arc}'}
            db_raw = z.read(db_arc)
            expected_db_sha = database.get('sha256')
            if not expected_db_sha:
                return {'verified': False, 'reason': 'database sha256 is missing'}
            if sha256_bytes(db_raw) != expected_db_sha:
                return {'verified': False, 'reason': 'sha256 mismatch for database'}
            sqlite_check = _validate_sqlite_bytes(db_raw)
            if not sqlite_check.get('ok'):
                return {'verified': False, 'reason': sqlite_check.get('reason')}
            for item in manifest.get('storage', []):
                arc = item.get('archive_path')
                if not arc or arc not in names:
                    return {'verified': False, 'reason': f'missing storage file {arc}'}
                if not _is_safe_archive_path(arc):
                    return {'verified': False, 'reason': f'unsafe storage path {arc}'}
                expected = item.get('sha256')
                if not expected:
                    return {'verified': False, 'reason': f'sha256 is missing for {arc}'}
                if sha256_bytes(z.read(arc)) != expected:
                    return {'verified': False, 'reason': f'sha256 mismatch for {arc}'}
    except RuntimeError as exc:
        return {'verified': False, 'reason': str(exc)}
    except zipfile.BadZipFile:
        return {'verified': False, 'reason': 'invalid zip archive'}
    return {
        'verified': True,
        'sha256': sha256_file(backup),
        'manifest': manifest,
        'sqlite': sqlite_check,
        'storage_files': len(manifest.get('storage', [])),
    }


def restore_backup(path: str | Path, target_dir: str | Path, *, overwrite: bool = False) -> dict:
    verification = verify_backup(path)
    if not verification.get('verified'):
        raise RuntimeError(verification.get('reason') or 'Backup verification failed')
    target = Path(target_dir).resolve()
    if target.exists() and any(target.iterdir()) and not overwrite:
        raise RuntimeError('Restore target is not empty')
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='autopassport-restore-', dir=target.parent))
    try:
        with zipfile.ZipFile(path) as z:
            _safe_extract(z, staging)
        if target.exists():
            if overwrite:
                shutil.rmtree(target)
            else:
                target.rmdir()
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        'restored': True,
        'target_dir': str(target),
        'database_exists': (target / 'database/autopassport.db').exists(),
        'storage_files': len([p for p in (target / 'storage').rglob('*') if p.is_file()]) if (target / 'storage').exists() else 0,
        'verified': True,
        'backup_sha256': verification.get('sha256'),
    }
