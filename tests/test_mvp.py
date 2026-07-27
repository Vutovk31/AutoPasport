import os, subprocess, sys
from pathlib import Path
from fastapi.testclient import TestClient

DEMO_VIN = "DEMO-VIN-00000001"
APP_MODULES = [
    "app.main",
    "app.application",
    "app.models",
    "app.database",
    "app.security",
    "app.domain",
    "app.pdf",
    "app.backup",
    "app.storage_quota",
    "app.share_limits",
]


def load_app(tmp_path, monkeypatch):
    root=Path(__file__).resolve().parents[1]
    if str(root) not in sys.path: sys.path.insert(0, str(root))
    db_url=f"sqlite:///{tmp_path/'test.db'}"; storage=tmp_path/'storage'
    env=os.environ.copy(); env.update({"DATABASE_URL":db_url,"STORAGE_PATH":str(storage),"PUBLIC_BASE_URL":"http://testserver"})
    result=subprocess.run([sys.executable,"-m","alembic","upgrade","head"],cwd=root,env=env,capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stderr
    monkeypatch.setenv("DATABASE_URL",db_url);monkeypatch.setenv("STORAGE_PATH",str(storage));monkeypatch.setenv("PUBLIC_BASE_URL","http://testserver")
    for module in APP_MODULES:
        sys.modules.pop(module, None)
    import app.main
    return app.main


def csrf(c): return {"X-CSRF-Token":c.cookies.get("autopassport_csrf")}
def register(c,email="owner@example.com"):
    r=c.post('/api/auth/register',data={'email':email,'password':'StrongPassword123'});assert r.status_code==201


def create_vehicle(c):
    r=c.post('/api/vehicles',headers=csrf(c),data={'vin':DEMO_VIN,'registration_number':'А000АА00','make':'Mazda','model':'3 BK','trim':'рестайлинг','year':2006,'current_mileage':178711,'purchase_date':'2024-08-10','purchase_mileage':'156000'})
    assert r.status_code==201;return r.json()['id']


def test_audit_soft_delete_and_odometer_protection(tmp_path,monkeypatch):
    main=load_app(tmp_path,monkeypatch)
    with TestClient(main.app) as c:
        register(c);vid=create_vehicle(c)
        r=c.post(f'/api/vehicles/{vid}/events',headers=csrf(c),data={'kind':'repair','event_date':'2026-07-01','mileage':'170000','title':'Замена сцепления','description':'Без документации','cost_rubles':'','cost_visible_to_public':'false'})
        eid=r.json()['id']
        r=c.patch(f'/api/events/{eid}',headers=csrf(c),data={'kind':'repair','event_date':'2026-07-01','mileage':'160000','title':'Замена сцепления','description':'Исправлено владельцем','cost_rubles':'','cost_visible_to_public':'false'})
        assert r.status_code==200 and r.json()['current_mileage']==178711
        audit=c.get(f'/api/events/{eid}/audit').json();assert [x['action'] for x in audit]==['created','updated']
        assert c.delete(f'/api/events/{eid}',headers=csrf(c)).status_code==204
        detail=c.get(f'/api/vehicles/{vid}').json();assert detail['vehicle']['current_mileage']==178711 and detail['events']==[]
        audit=c.get(f'/api/events/{eid}/audit').json();assert audit[-1]['action']=='soft_deleted'


def test_contextual_trust_and_public_share(tmp_path,monkeypatch):
    main=load_app(tmp_path,monkeypatch)
    with TestClient(main.app) as c:
        register(c);vid=create_vehicle(c)
        repair=c.post(f'/api/vehicles/{vid}/events',headers=csrf(c),data={'kind':'repair','event_date':'2026-06-01','mileage':'','title':'Замена шаровой','description':'','cost_rubles':'1500','cost_visible_to_public':'true'}).json()['id']
        quote=c.post(f'/api/events/{repair}/attachments',headers=csrf(c),data={'evidence_type':'correspondence'},files={'file':('quote.jpg',b'\xff\xd8\xffDATA','image/jpeg')})
        assert quote.json()['trust_level']=='declared'
        work=c.post(f'/api/events/{repair}/attachments',headers=csrf(c),data={'evidence_type':'work_order'},files={'file':('order.pdf',b'%PDF-1.4 DATA','application/pdf')})
        assert work.json()['trust_level']=='verified'
        share=c.post(f'/api/vehicles/{vid}/share',headers=csrf(c)).json();payload=c.get(share['url'].replace('http://testserver','') .replace('/p/','/api/public/')).json()
        assert payload['vehicle']['vin']!=DEMO_VIN
        assert payload['events'][0]['cost_rubles']==1500
        assert c.delete(f"/api/share/{share['id']}",headers=csrf(c)).status_code==204
        assert c.get(share['url'].replace('http://testserver','').replace('/p/','/api/public/')).status_code==404


def test_readiness_and_frontend(tmp_path,monkeypatch):
    main=load_app(tmp_path,monkeypatch)
    with TestClient(main.app) as c:
        assert c.get('/ready').status_code==200
        page=c.get('/');assert page.status_code==200 and 'Ссылка на 1 час' in page.text


def test_service_visit_items_cost_statuses_and_public_payload(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as c:
        register(c)
        vid = create_vehicle(c)
        payload = {
            "kind": "repair_visit",
            "visit_date": "2026-07-01",
            "mileage": 178000,
            "title": "Замена сцепления и масла КПП",
            "location": "знакомый мастер",
            "description": "Работа 5 000 ₽ включает снятие КПП, замену сцепления и замену масла КПП.",
            "total_cost_rubles": 25900,
            "total_cost_status": "known",
            "total_cost_visible_to_public": True,
            "items": [
                {"item_type": "part", "title": "Комплект сцепления ZF Russia", "brand": "ZF Russia", "cost_rubles": 18000, "cost_status": "known"},
                {"item_type": "operation", "title": "Замена выжимного подшипника", "cost_status": "included_in_visit"},
                {"item_type": "fluid", "title": "MANNOL BASIC PLUS Getriebeoel 75W-90", "brand": "Mannol", "part_number": "8108", "quantity": "3", "unit": "л", "cost_rubles": 2900, "cost_status": "known"},
                {"item_type": "labor", "title": "Снятие КПП + замена сцепления + замена масла КПП", "cost_rubles": 5000, "cost_status": "known"},
            ],
        }
        created = c.post(f"/api/vehicles/{vid}/visits", headers=csrf(c), json=payload)
        assert created.status_code == 201, created.text
        visit_id = created.json()["id"]
        detail = c.get(f"/api/vehicles/{vid}").json()
        assert detail["vehicle"]["current_mileage"] == 178711
        visit = detail["visits"][0]
        assert visit["total_cost_rubles"] == 25900
        assert sum(i["cost_rubles"] or 0 for i in visit["items"]) == 25900
        assert any(i["cost_status"] == "included_in_visit" and i["cost_rubles"] is None for i in visit["items"])

        uploaded = c.post(
            f"/api/visits/{visit_id}/attachments",
            headers=csrf(c),
            data={"evidence_type": "work_order"},
            files={"file": ("order.pdf", b"%PDF-1.4 DATA", "application/pdf")},
        )
        assert uploaded.status_code == 201
        assert uploaded.json()["trust_level"] == "verified"
        assert c.delete(f"/api/attachments/{uploaded.json()['id']}", headers=csrf(c)).status_code == 204
        detail_after_delete = c.get(f"/api/vehicles/{vid}").json()
        assert detail_after_delete["visits"][0]["trust_level"] == "declared"
        uploaded = c.post(
            f"/api/visits/{visit_id}/attachments",
            headers=csrf(c),
            data={"evidence_type": "work_order"},
            files={"file": ("order2.pdf", b"%PDF-1.4 DATA", "application/pdf")},
        )
        assert uploaded.json()["trust_level"] == "verified"

        share = c.post(f"/api/vehicles/{vid}/share", headers=csrf(c)).json()
        public = c.get(share["url"].replace("http://testserver", "").replace("/p/", "/api/public/")).json()
        assert public["visits"][0]["total_cost_rubles"] == 25900
        assert any(i["cost_status"] == "included_in_visit" for i in public["visits"][0]["items"])
        assert public["vehicle"]["vin"] != DEMO_VIN


def test_service_visit_soft_delete_audit_and_no_odometer_rollback(tmp_path, monkeypatch):
    main = load_app(tmp_path, monkeypatch)
    with TestClient(main.app) as c:
        register(c)
        vid = create_vehicle(c)
        created = c.post(
            f"/api/vehicles/{vid}/visits",
            headers=csrf(c),
            json={
                "kind": "repair_visit",
                "visit_date": "2026-06-01",
                "mileage": 177000,
                "title": "Ремонт подвески",
                "total_cost_rubles": 15600,
                "total_cost_status": "known",
                "items": [{"item_type": "part", "title": "Датчик давления", "cost_rubles": 800, "cost_status": "known"}],
            },
        ).json()
        visit_id = created["id"]
        updated = c.patch(
            f"/api/visits/{visit_id}",
            headers=csrf(c),
            json={"mileage": 120000, "title": "Ремонт подвески уточнён", "total_cost_status": "known", "total_cost_rubles": 15600},
        )
        assert updated.status_code == 200
        assert updated.json()["current_mileage"] == 178711
        assert c.delete(f"/api/visits/{visit_id}", headers=csrf(c)).status_code == 204
        detail = c.get(f"/api/vehicles/{vid}").json()
        assert detail["vehicle"]["current_mileage"] == 178711
        assert detail["visits"] == []
        audit_rows = c.get(f"/api/visits/{visit_id}/audit").json()
        assert [x["action"] for x in audit_rows] == ["created", "updated", "soft_deleted"]
