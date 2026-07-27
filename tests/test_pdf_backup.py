import os
import subprocess
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from pypdf import PdfReader

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


def register(c):
    r = c.post('/api/auth/register', data={'email':'owner@example.com', 'password':'StrongPassword123'})
    assert r.status_code == 201


def create_vehicle(c):
    r = c.post('/api/vehicles', headers=csrf(c), data={
        'vin':DEMO_VIN, 'registration_number':'А000АА00', 'make':'Mazda', 'model':'3 BK',
        'trim':'рестайлинг', 'year':2006, 'current_mileage':178711, 'purchase_date':'2024-08-10', 'purchase_mileage':'156000'
    })
    assert r.status_code == 201, r.text
    return r.json()['id']


def create_clutch_visit(c, vid):
    payload = {
        'kind': 'repair_visit',
        'visit_date': '2026-07-01',
        'mileage': 178000,
        'title': 'Замена сцепления и масла КПП',
        'location': 'знакомый мастер',
        'description': 'Работа 5 000 ₽ включает снятие КПП, замену сцепления и замену масла КПП.',
        'total_cost_rubles': 25900,
        'total_cost_status': 'known',
        'total_cost_visible_to_public': True,
        'items': [
            {'item_type':'part','title':'Комплект сцепления ZF Russia','brand':'ZF Russia','cost_rubles':18000,'cost_status':'known'},
            {'item_type':'operation','title':'Замена выжимного подшипника','cost_status':'included_in_visit'},
            {'item_type':'fluid','title':'MANNOL BASIC PLUS Getriebeoel 75W-90','brand':'Mannol','part_number':'8108','quantity':'3','unit':'л','cost_rubles':2900,'cost_status':'known'},
            {'item_type':'labor','title':'Снятие КПП + замена сцепления + замена масла КПП','cost_rubles':5000,'cost_status':'known'},
        ],
    }
    r = c.post(f'/api/vehicles/{vid}/visits', headers=csrf(c), json=payload)
    assert r.status_code == 201, r.text
    return r.json()['id']


def pdf_text(raw: bytes) -> str:
    path = Path('/tmp/autopassport-test.pdf')
    path.write_bytes(raw)
    return '\n'.join(page.extract_text() or '' for page in PdfReader(str(path)).pages)


def test_owner_and_public_pdf(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as c:
        register(c)
        vid = create_vehicle(c)
        create_clutch_visit(c, vid)
        owner_pdf = c.get(f'/api/vehicles/{vid}/pdf')
        assert owner_pdf.status_code == 200
        assert owner_pdf.headers['content-type'].startswith('application/pdf')
        assert owner_pdf.content.startswith(b'%PDF-')
        owner_text = pdf_text(owner_pdf.content)
        assert 'AutoPassport' in owner_text
        assert 'Mazda' in owner_text
        assert DEMO_VIN in owner_text

        share = c.post(f'/api/vehicles/{vid}/share', headers=csrf(c)).json()
        token = share['url'].rsplit('/', 1)[-1]
        public_pdf = c.get(f'/api/public/{token}/pdf')
        assert public_pdf.status_code == 200
        public_text = pdf_text(public_pdf.content)
        assert 'AutoPassport' in public_text
        assert DEMO_VIN not in public_text
        assert 'DEMO-' in public_text
        assert '25 900' in public_text


def test_admin_backup_verify_and_restore(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as c:
        register(c)
        vid = create_vehicle(c)
        visit_id = create_clutch_visit(c, vid)
        uploaded = c.post(
            f'/api/visits/{visit_id}/attachments',
            headers=csrf(c),
            data={'evidence_type':'work_order'},
            files={'file':('order.pdf', b'%PDF-1.4 DATA', 'application/pdf')},
        )
        assert uploaded.status_code == 201
        forbidden = c.post('/api/admin/backups')
        assert forbidden.status_code == 403
        created = c.post('/api/admin/backups', headers={'X-Admin-Token': 'test-backup-token'})
        assert created.status_code == 201, created.text
        backup_name = created.json()['name']
        assert created.json()['size_bytes'] > 0
        verified = c.get(f'/api/admin/backups/{backup_name}/verify', headers={'X-Admin-Token': 'test-backup-token'})
        assert verified.status_code == 200
        assert verified.json()['verified'] is True

        restored = main.restore_backup(created.json()['path'], tmp_path / 'restore-target')
        assert restored['restored'] is True
        assert restored['database_exists'] is True
        assert restored['storage_files'] >= 1
