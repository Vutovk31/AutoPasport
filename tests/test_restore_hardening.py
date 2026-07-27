from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

DEMO_VIN = "DEMO-VIN-00000001"


def load_app(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    storage = tmp_path / 'storage'
    backups = tmp_path / 'backups'
    env = os.environ.copy()
    env.update({
        'DATABASE_URL': db_url,
        'STORAGE_PATH': str(storage),
        'BACKUP_PATH': str(backups),
        'PUBLIC_BASE_URL': 'http://testserver',
        'ADMIN_BACKUP_TOKEN': 'test-backup-token',
    })
    result = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=root, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    monkeypatch.setenv('DATABASE_URL', db_url)
    monkeypatch.setenv('STORAGE_PATH', str(storage))
    monkeypatch.setenv('BACKUP_PATH', str(backups))
    monkeypatch.setenv('PUBLIC_BASE_URL', 'http://testserver')
    monkeypatch.setenv('ADMIN_BACKUP_TOKEN', 'test-backup-token')
    for m in ['app.main','app.models','app.database','app.security','app.domain','app.pdf','app.backup']:
        sys.modules.pop(m, None)
    import app.main
    return app.main


def csrf(c):
    return {'X-CSRF-Token': c.cookies.get('autopassport_csrf')}


def create_restorable_backup(c):
    r = c.post('/api/auth/register', data={'email':'owner@example.com', 'password':'StrongPassword123'})
    assert r.status_code == 201
    vehicle = c.post('/api/vehicles', headers=csrf(c), data={
        'vin':DEMO_VIN, 'registration_number':'А000АА00', 'make':'Mazda', 'model':'3 BK',
        'trim':'рестайлинг', 'year':2006, 'current_mileage':178711, 'purchase_date':'2024-08-10', 'purchase_mileage':'156000'
    })
    assert vehicle.status_code == 201, vehicle.text
    vid = vehicle.json()['id']
    visit = c.post(f'/api/vehicles/{vid}/visits', headers=csrf(c), json={
        'kind': 'repair_visit', 'visit_date': '2026-07-01', 'mileage': 178000,
        'title': 'Замена сцепления и масла КПП', 'total_cost_rubles': 25900,
        'total_cost_status': 'known', 'total_cost_visible_to_public': True,
        'items': [{'item_type':'part','title':'Комплект сцепления ZF Russia','cost_rubles':18000,'cost_status':'known'}],
    })
    assert visit.status_code == 201, visit.text
    upload = c.post(
        f"/api/visits/{visit.json()['id']}/attachments",
        headers=csrf(c),
        data={'evidence_type':'work_order'},
        files={'file':('order.pdf', b'%PDF-1.4 DATA', 'application/pdf')},
    )
    assert upload.status_code == 201, upload.text
    created = c.post('/api/admin/backups', headers={'X-Admin-Token': 'test-backup-token'})
    assert created.status_code == 201, created.text
    return created.json()


def test_backup_manifest_contains_database_checksum_and_restore_check_endpoint(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as c:
        backup = create_restorable_backup(c)
        with zipfile.ZipFile(backup['path']) as z:
            manifest = json.loads(z.read('manifest.json'))
        assert manifest['database']['sha256']
        assert manifest['database']['size'] > 0
        verified = c.get(f"/api/admin/backups/{backup['name']}/verify", headers={'X-Admin-Token': 'test-backup-token'})
        assert verified.status_code == 200
        assert verified.json()['verified'] is True
        restore_check = c.post(f"/api/admin/backups/{backup['name']}/restore-check", headers={'X-Admin-Token': 'test-backup-token'})
        assert restore_check.status_code == 200, restore_check.text
        assert restore_check.json()['database_exists'] is True
        assert restore_check.json()['storage_files'] >= 1


def test_restore_refuses_non_empty_target_unless_overwrite(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as c:
        backup = create_restorable_backup(c)
    target = tmp_path / 'restore-target'
    target.mkdir()
    (target / 'keep.txt').write_text('keep', encoding='utf-8')
    with pytest.raises(RuntimeError, match='not empty'):
        main.restore_backup(backup['path'], target)
    assert (target / 'keep.txt').read_text(encoding='utf-8') == 'keep'
    restored = main.restore_backup(backup['path'], target, overwrite=True)
    assert restored['database_exists'] is True
    assert not (target / 'keep.txt').exists()


def test_verify_backup_rejects_tampered_database(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as c:
        backup = create_restorable_backup(c)
    tampered = tmp_path / 'tampered-db.zip'
    with zipfile.ZipFile(backup['path']) as source, zipfile.ZipFile(tampered, 'w') as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == 'database/autopassport.db':
                data = b'not sqlite'
            target.writestr(item, data)
    result = main.verify_backup(tampered)
    assert result['verified'] is False
    assert 'database' in result['reason'] or 'sha256 mismatch' in result['reason']


def test_verify_backup_rejects_path_traversal(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    unsafe = tmp_path / 'unsafe.zip'
    with zipfile.ZipFile(unsafe, 'w') as z:
        z.writestr('../escape.txt', 'owned')
        z.writestr('manifest.json', '{}')
    result = main.verify_backup(unsafe)
    assert result['verified'] is False
    assert 'Unsafe archive entry' in result['reason']


def test_restored_database_can_boot_ready_endpoint(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as c:
        backup = create_restorable_backup(c)
    restore_target = tmp_path / 'restored-runtime'
    main.restore_backup(backup['path'], restore_target)

    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{restore_target / 'database' / 'autopassport.db'}")
    monkeypatch.setenv('STORAGE_PATH', str(restore_target / 'storage'))
    monkeypatch.setenv('BACKUP_PATH', str(tmp_path / 'restored-backups'))
    monkeypatch.setenv('PUBLIC_BASE_URL', 'http://testserver')
    monkeypatch.setenv('ADMIN_BACKUP_TOKEN', 'test-backup-token')
    for m in ['app.main','app.models','app.database','app.security','app.domain','app.pdf','app.backup']:
        sys.modules.pop(m, None)
    import app.main as restored_main
    with TestClient(restored_main.app) as restored_client:
        assert restored_client.get('/health').json()['version'] == '0.25.0'
        assert restored_client.get('/ready').status_code == 200
