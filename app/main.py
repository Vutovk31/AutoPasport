from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import hashlib, os, secrets, hmac
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import Body, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, database_url
from .domain import audit, event_snapshot, item_snapshot, kopecks_from_rubles, mask_vin, now, recalc_trust, recalc_visit_trust, rubles_from_kopecks, validate_cost_status, validate_item_type, validate_visit_kind, visit_audit, visit_snapshot
from .models import Attachment, EventAudit, HistoryEvent, ServiceItem, ServiceVisit, SessionToken, ShareLink, User, Vehicle, VisitAudit
from .security import SESSION_COOKIE, current_user, db, mutation_guard, password_hash, password_valid, set_session, sha
from .pdf import build_passport_pdf
from .backup import BACKUP_DIR, create_backup, verify_backup, restore_backup

STATIC = Path(__file__).resolve().parent / "static"
STORAGE = Path(os.getenv("STORAGE_PATH", "./data/storage")).resolve(); STORAGE.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5*1024*1024)))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
app = FastAPI(title="AutoPassport", version="0.24.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

def own_vehicle(session, user, vehicle_id):
    v = session.get(Vehicle, vehicle_id)
    if not v: raise HTTPException(404, "Vehicle not found")
    if v.owner_id != user.id: raise HTTPException(403, "Forbidden")
    return v

def own_event(session, user, event_id):
    e = session.get(HistoryEvent, event_id)
    if not e: raise HTTPException(404, "Event not found")
    return e, own_vehicle(session, user, e.vehicle_id)

def own_visit(session, user, visit_id):
    visit = session.get(ServiceVisit, visit_id)
    if not visit: raise HTTPException(404, "Service visit not found")
    return visit, own_vehicle(session, user, visit.vehicle_id)

def migrations_current():
    config = Config("alembic.ini"); config.set_main_option("sqlalchemy.url", database_url)
    expected = ScriptDirectory.from_config(config).get_current_head()
    with engine.connect() as c: current = MigrationContext.configure(c).get_current_revision()
    return current == expected

def dt_aware(value): return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

def _attachment_rows(session, *, event_id=None, visit_id=None):
    query = select(Attachment).where(Attachment.is_deleted.is_(False))
    if event_id is not None:
        query = query.where(Attachment.event_id == event_id)
    if visit_id is not None:
        query = query.where(Attachment.visit_id == visit_id)
    return list(session.scalars(query))

def serialize_item(item: ServiceItem):
    return {
        **item_snapshot(item),
        "cost_rubles": rubles_from_kopecks(item.cost_kopecks),
    }

def serialize_visit(session, visit: ServiceVisit, include_deleted_items=False):
    items_query = select(ServiceItem).where(ServiceItem.visit_id == visit.id)
    if not include_deleted_items:
        items_query = items_query.where(ServiceItem.is_deleted.is_(False))
    items = list(session.scalars(items_query.order_by(ServiceItem.item_type, ServiceItem.title)))
    atts = _attachment_rows(session, visit_id=visit.id)
    return {
        "id": visit.id,
        "kind": visit.kind,
        "visit_date": visit.visit_date.isoformat(),
        "mileage": visit.mileage,
        "title": visit.title,
        "location": visit.location,
        "description": visit.description,
        "total_cost_kopecks": visit.total_cost_kopecks,
        "total_cost_rubles": rubles_from_kopecks(visit.total_cost_kopecks),
        "total_cost_status": visit.total_cost_status,
        "total_cost_visible_to_public": visit.total_cost_visible_to_public,
        "trust_level": visit.trust_level,
        "revision": visit.revision,
        "items": [serialize_item(i) for i in items],
        "attachments": [{"id":a.id,"original_name":a.original_name,"evidence_type":a.evidence_type,"sha256":a.sha256} for a in atts],
    }

def service_item_from_payload(visit_id, payload):
    cost_status = validate_cost_status(payload.get("cost_status", "unknown"))
    cost_value = payload.get("cost_rubles")
    return ServiceItem(
        visit_id=visit_id,
        item_type=validate_item_type(payload.get("item_type", "operation")),
        title=(payload.get("title") or "").strip(),
        description=(payload.get("description") or "").strip(),
        brand=(payload.get("brand") or "").strip() or None,
        part_number=(payload.get("part_number") or "").strip() or None,
        quantity=str(payload.get("quantity")).strip() if payload.get("quantity") not in (None, "") else None,
        unit=(payload.get("unit") or "").strip() or None,
        cost_kopecks=kopecks_from_rubles(cost_value) if cost_status == "known" else None,
        cost_status=cost_status,
    )

@app.get("/", include_in_schema=False)
def index(): return FileResponse(STATIC/"index.html")

@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(STATIC/"manifest.webmanifest", media_type="application/manifest+json")

@app.get("/offline.html", include_in_schema=False)
def offline_page():
    return FileResponse(STATIC/"offline.html")

@app.get("/service-worker.js", include_in_schema=False)
def service_worker():
    return FileResponse(STATIC/"service-worker.js", media_type="application/javascript")
@app.get("/health")
def health(): return {"status":"ok","version":"0.24.0"}
@app.get("/ready")
def ready():
    if not migrations_current(): raise HTTPException(503, "Migrations are not current")
    return {"status":"ready","migrations":True}

@app.post("/api/auth/register", status_code=201)
def register(response: Response, email: str=Form(...), password: str=Form(...), session: Session=Depends(db)):
    email=email.strip().lower()
    if len(password)<10: raise HTTPException(422,"Password must contain at least 10 characters")
    if session.scalar(select(User).where(User.email==email)): raise HTTPException(409,"Email already registered")
    user=User(email=email,password_hash=password_hash(password)); session.add(user); session.flush(); set_session(response,session,user)
    return {"authenticated":True}
@app.post("/api/auth/login")
def login(response: Response,email: str=Form(...),password: str=Form(...),session: Session=Depends(db)):
    user=session.scalar(select(User).where(User.email==email.strip().lower()))
    if not user or not password_valid(password,user.password_hash): raise HTTPException(401,"Invalid credentials")
    set_session(response,session,user); return {"authenticated":True}
@app.post("/api/auth/logout", status_code=204)
def logout(response: Response,user: User=Depends(mutation_guard),session: Session=Depends(db),token: str|None=Depends(lambda: None)):
    response.delete_cookie(SESSION_COOKIE,path="/"); response.delete_cookie("autopassport_csrf",path="/")
@app.get("/api/me")
def me(user: User=Depends(current_user)): return {"id":user.id,"email":user.email}

@app.get("/api/vehicles")
def vehicles(user: User=Depends(current_user),session: Session=Depends(db)):
    rows=session.scalars(select(Vehicle).where(Vehicle.owner_id==user.id).order_by(Vehicle.make,Vehicle.model))
    return [{"id":v.id,"make":v.make,"model":v.model,"trim":v.trim,"year":v.year,"vin":v.vin,"registration_number":v.registration_number,"current_mileage":v.current_mileage} for v in rows]

@app.post("/api/vehicles", status_code=201)
def create_vehicle(vin: str=Form(...),registration_number: str=Form(""),make: str=Form(...),model: str=Form(...),trim: str=Form(""),year: int=Form(...),current_mileage: int=Form(...),purchase_date: str=Form(""),purchase_mileage: str=Form(""),user: User=Depends(mutation_guard),session: Session=Depends(db)):
    vin=vin.strip().upper()
    if len(vin)!=17: raise HTTPException(422,"VIN must contain 17 characters")
    vehicle=Vehicle(owner_id=user.id,vin=vin,registration_number=registration_number.strip().upper() or None,make=make.strip(),model=model.strip(),trim=trim.strip() or None,year=year,current_mileage=current_mileage,purchase_date=date.fromisoformat(purchase_date) if purchase_date else None,purchase_mileage=int(purchase_mileage) if purchase_mileage else None)
    session.add(vehicle); session.commit(); return {"id":vehicle.id}

@app.get("/api/vehicles/{vehicle_id}")
def vehicle_detail(vehicle_id: str,user: User=Depends(current_user),session: Session=Depends(db)):
    v=own_vehicle(session,user,vehicle_id)
    events=list(session.scalars(select(HistoryEvent).where(HistoryEvent.vehicle_id==v.id,HistoryEvent.is_deleted.is_(False)).order_by(HistoryEvent.event_date.desc())))
    out=[]
    for e in events:
        atts=list(session.scalars(select(Attachment).where(Attachment.event_id==e.id,Attachment.is_deleted.is_(False))))
        out.append({"id":e.id,"kind":e.kind,"event_date":e.event_date.isoformat(),"mileage":e.mileage,"title":e.title,"description":e.description,"cost_kopecks":e.cost_kopecks,"cost_visible_to_public":e.cost_visible_to_public,"trust_level":e.trust_level,"revision":e.revision,"attachments":[{"id":a.id,"original_name":a.original_name,"evidence_type":a.evidence_type} for a in atts]})
    visits = list(session.scalars(select(ServiceVisit).where(ServiceVisit.vehicle_id==v.id, ServiceVisit.is_deleted.is_(False)).order_by(ServiceVisit.visit_date.desc())))
    return {"vehicle":{"id":v.id,"make":v.make,"model":v.model,"trim":v.trim,"year":v.year,"vin":v.vin,"registration_number":v.registration_number,"current_mileage":v.current_mileage,"purchase_date":v.purchase_date.isoformat() if v.purchase_date else None,"purchase_mileage":v.purchase_mileage},"events":out,"visits":[serialize_visit(session,x) for x in visits]}

@app.post("/api/vehicles/{vehicle_id}/events",status_code=201)
def create_event(vehicle_id: str,kind: str=Form("repair"),event_date: str=Form(...),mileage: str=Form(""),title: str=Form(...),description: str=Form(""),cost_rubles: str=Form(""),cost_visible_to_public: bool=Form(False),user: User=Depends(mutation_guard),session: Session=Depends(db)):
    v=own_vehicle(session,user,vehicle_id)
    m=int(mileage) if mileage else None
    if m is not None and m>v.current_mileage: v.current_mileage=m
    e=HistoryEvent(vehicle_id=v.id,kind=kind,event_date=date.fromisoformat(event_date),mileage=m,title=title.strip(),description=description.strip(),cost_kopecks=round(float(cost_rubles.replace(',','.'))*100) if cost_rubles else None,cost_visible_to_public=cost_visible_to_public,trust_level="declared",revision=1)
    session.add(e); session.flush(); audit(session,e,user.id,"created",after=event_snapshot(e)); session.commit(); return {"id":e.id}

@app.patch("/api/events/{event_id}")
def update_event(event_id: str,kind: str=Form(...),event_date: str=Form(...),mileage: str=Form(""),title: str=Form(...),description: str=Form(""),cost_rubles: str=Form(""),cost_visible_to_public: bool=Form(False),user: User=Depends(mutation_guard),session: Session=Depends(db)):
    e,v=own_event(session,user,event_id)
    if e.is_deleted: raise HTTPException(409,"Deleted event cannot be edited")
    before=event_snapshot(e); e.revision+=1; e.kind=kind; e.event_date=date.fromisoformat(event_date); e.mileage=int(mileage) if mileage else None; e.title=title.strip(); e.description=description.strip(); e.cost_kopecks=round(float(cost_rubles.replace(',','.'))*100) if cost_rubles else None; e.cost_visible_to_public=cost_visible_to_public
    if e.mileage is not None and e.mileage>v.current_mileage: v.current_mileage=e.mileage
    audit(session,e,user.id,"updated",before,event_snapshot(e)); session.commit(); return {"revision":e.revision,"current_mileage":v.current_mileage}

@app.delete("/api/events/{event_id}",status_code=204)
def soft_delete_event(event_id: str,user: User=Depends(mutation_guard),session: Session=Depends(db)):
    e,_=own_event(session,user,event_id)
    if e.is_deleted: return
    before=event_snapshot(e); e.revision+=1; e.is_deleted=True; e.deleted_at=now(); audit(session,e,user.id,"soft_deleted",before,event_snapshot(e)); session.commit()

@app.get("/api/events/{event_id}/audit")
def audit_log(event_id: str,user: User=Depends(current_user),session: Session=Depends(db)):
    e,_=own_event(session,user,event_id)
    rows=session.scalars(select(EventAudit).where(EventAudit.event_id==e.id).order_by(EventAudit.created_at))
    return [{"action":r.action,"revision":r.revision,"before":r.before_json,"after":r.after_json,"created_at":r.created_at.isoformat()} for r in rows]

@app.post("/api/events/{event_id}/attachments",status_code=201)
async def upload_attachment(event_id: str,evidence_type: str=Form(...),file: UploadFile=File(...),user: User=Depends(mutation_guard),session: Session=Depends(db)):
    e,_=own_event(session,user,event_id)
    if e.is_deleted: raise HTTPException(409,"Cannot attach to deleted event")
    allowed={"receipt","work_order","service_act","diagnostic_report","estimate","correspondence","mechanic_confirmation","photo_after"}
    if evidence_type not in allowed: raise HTTPException(422,"Unsupported evidence type")
    data=await file.read(MAX_UPLOAD_BYTES+1)
    if len(data)>MAX_UPLOAD_BYTES: raise HTTPException(413,"File too large")
    signatures={"application/pdf":b"%PDF-","image/png":b"\x89PNG\r\n\x1a\n","image/jpeg":b"\xff\xd8\xff"}
    sig=signatures.get(file.content_type or "")
    if not sig or not data.startswith(sig): raise HTTPException(415,"Unsupported or spoofed file")
    suffix={"application/pdf":".pdf","image/png":".png","image/jpeg":".jpg"}[file.content_type]
    stored=secrets.token_urlsafe(18)+suffix; physical=STORAGE/stored; physical.write_bytes(data)
    try:
        a=Attachment(event_id=e.id,original_name=Path(file.filename or "document").name,stored_name=stored,media_type=file.content_type,evidence_type=evidence_type,size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        session.add(a); session.flush(); before=event_snapshot(e); recalc_trust(session,e); audit(session,e,user.id,"attachment_added",before,event_snapshot(e)); session.commit(); return {"id":a.id,"trust_level":e.trust_level}
    except Exception:
        session.rollback(); physical.unlink(missing_ok=True); raise

@app.delete("/api/attachments/{attachment_id}",status_code=204)
def soft_delete_attachment(attachment_id: str,user: User=Depends(mutation_guard),session: Session=Depends(db)):
    a=session.get(Attachment,attachment_id)
    if not a: raise HTTPException(404,"Attachment not found")
    if a.is_deleted: return
    if a.event_id:
        e,_=own_event(session,user,a.event_id)
        before=event_snapshot(e); a.is_deleted=True; a.deleted_at=now(); session.flush(); recalc_trust(session,e); audit(session,e,user.id,"attachment_soft_deleted",before,event_snapshot(e)); session.commit(); return
    if a.visit_id:
        visit,_=own_visit(session,user,a.visit_id)
        before=visit_snapshot(visit); a.is_deleted=True; a.deleted_at=now(); session.flush(); recalc_visit_trust(session,visit); visit_audit(session,visit,user.id,"attachment_soft_deleted",before,visit_snapshot(visit)); session.commit(); return
    raise HTTPException(409,"Detached attachment cannot be resolved")


@app.get("/api/vehicles/{vehicle_id}/visits")
def list_visits(vehicle_id: str,user: User=Depends(current_user),session: Session=Depends(db)):
    v=own_vehicle(session,user,vehicle_id)
    visits=session.scalars(select(ServiceVisit).where(ServiceVisit.vehicle_id==v.id,ServiceVisit.is_deleted.is_(False)).order_by(ServiceVisit.visit_date.desc()))
    return [serialize_visit(session,visit) for visit in visits]

@app.post("/api/vehicles/{vehicle_id}/visits",status_code=201)
def create_visit(vehicle_id: str,payload: dict=Body(...),user: User=Depends(mutation_guard),session: Session=Depends(db)):
    v=own_vehicle(session,user,vehicle_id)
    try:
        kind=validate_visit_kind(payload.get("kind","repair_visit"))
        cost_status=validate_cost_status(payload.get("total_cost_status","unknown"))
    except ValueError as exc:
        raise HTTPException(422,str(exc))
    mileage=payload.get("mileage")
    mileage=int(mileage) if mileage not in (None,"") else None
    if mileage is not None and mileage>v.current_mileage: v.current_mileage=mileage
    visit=ServiceVisit(
        vehicle_id=v.id,
        kind=kind,
        visit_date=date.fromisoformat(payload["visit_date"]),
        mileage=mileage,
        title=(payload.get("title") or "").strip(),
        location=(payload.get("location") or "").strip() or None,
        description=(payload.get("description") or "").strip(),
        total_cost_kopecks=kopecks_from_rubles(payload.get("total_cost_rubles")) if cost_status=="known" else None,
        total_cost_status=cost_status,
        total_cost_visible_to_public=bool(payload.get("total_cost_visible_to_public",False)),
        trust_level="declared",
        revision=1,
    )
    if not visit.title: raise HTTPException(422,"Visit title is required")
    session.add(visit); session.flush()
    for row in payload.get("items",[]):
        item=service_item_from_payload(visit.id,row)
        if not item.title: raise HTTPException(422,"Item title is required")
        session.add(item)
    session.flush(); visit_audit(session,visit,user.id,"created",after=visit_snapshot(visit)); session.commit(); session.refresh(visit)
    return {"id":visit.id,"revision":visit.revision,"current_mileage":v.current_mileage}

@app.patch("/api/visits/{visit_id}")
def update_visit(visit_id: str,payload: dict=Body(...),user: User=Depends(mutation_guard),session: Session=Depends(db)):
    visit,v=own_visit(session,user,visit_id)
    if visit.is_deleted: raise HTTPException(409,"Deleted visit cannot be edited")
    try:
        kind=validate_visit_kind(payload.get("kind",visit.kind))
        cost_status=validate_cost_status(payload.get("total_cost_status",visit.total_cost_status))
    except ValueError as exc:
        raise HTTPException(422,str(exc))
    before=visit_snapshot(visit)
    visit.revision+=1
    visit.kind=kind
    visit.visit_date=date.fromisoformat(payload.get("visit_date",visit.visit_date.isoformat()))
    mileage=payload.get("mileage",visit.mileage)
    visit.mileage=int(mileage) if mileage not in (None,"") else None
    visit.title=(payload.get("title",visit.title) or "").strip()
    visit.location=(payload.get("location",visit.location) or "").strip() or None
    visit.description=(payload.get("description",visit.description) or "").strip()
    visit.total_cost_status=cost_status
    visit.total_cost_kopecks=kopecks_from_rubles(payload.get("total_cost_rubles")) if cost_status=="known" and "total_cost_rubles" in payload else visit.total_cost_kopecks
    if cost_status!="known": visit.total_cost_kopecks=None
    visit.total_cost_visible_to_public=bool(payload.get("total_cost_visible_to_public",visit.total_cost_visible_to_public))
    if visit.mileage is not None and visit.mileage>v.current_mileage: v.current_mileage=visit.mileage
    visit_audit(session,visit,user.id,"updated",before,visit_snapshot(visit)); session.commit()
    return {"revision":visit.revision,"current_mileage":v.current_mileage}

@app.delete("/api/visits/{visit_id}",status_code=204)
def soft_delete_visit(visit_id: str,user: User=Depends(mutation_guard),session: Session=Depends(db)):
    visit,_=own_visit(session,user,visit_id)
    if visit.is_deleted: return
    before=visit_snapshot(visit)
    visit.revision+=1; visit.is_deleted=True; visit.deleted_at=now()
    for item in session.scalars(select(ServiceItem).where(ServiceItem.visit_id==visit.id,ServiceItem.is_deleted.is_(False))):
        item.is_deleted=True; item.deleted_at=now()
    visit_audit(session,visit,user.id,"soft_deleted",before,visit_snapshot(visit)); session.commit()

@app.post("/api/visits/{visit_id}/items",status_code=201)
def add_visit_item(visit_id: str,payload: dict=Body(...),user: User=Depends(mutation_guard),session: Session=Depends(db)):
    visit,_=own_visit(session,user,visit_id)
    if visit.is_deleted: raise HTTPException(409,"Deleted visit cannot be edited")
    try:
        item=service_item_from_payload(visit.id,payload)
    except ValueError as exc:
        raise HTTPException(422,str(exc))
    if not item.title: raise HTTPException(422,"Item title is required")
    before=visit_snapshot(visit)
    visit.revision+=1
    session.add(item); session.flush(); visit_audit(session,visit,user.id,"item_added",before,visit_snapshot(visit)); session.commit(); session.refresh(item)
    return {"id":item.id,"revision":visit.revision}

@app.get("/api/visits/{visit_id}/audit")
def visit_audit_log(visit_id: str,user: User=Depends(current_user),session: Session=Depends(db)):
    visit,_=own_visit(session,user,visit_id)
    rows=session.scalars(select(VisitAudit).where(VisitAudit.visit_id==visit.id).order_by(VisitAudit.created_at))
    return [{"action":r.action,"revision":r.revision,"before":r.before_json,"after":r.after_json,"created_at":r.created_at.isoformat()} for r in rows]

@app.post("/api/visits/{visit_id}/attachments",status_code=201)
async def upload_visit_attachment(visit_id: str,evidence_type: str=Form(...),file: UploadFile=File(...),user: User=Depends(mutation_guard),session: Session=Depends(db)):
    visit,_=own_visit(session,user,visit_id)
    if visit.is_deleted: raise HTTPException(409,"Cannot attach to deleted visit")
    allowed={"receipt","work_order","service_act","diagnostic_report","estimate","correspondence","mechanic_confirmation","photo_after"}
    if evidence_type not in allowed: raise HTTPException(422,"Unsupported evidence type")
    data=await file.read(MAX_UPLOAD_BYTES+1)
    if len(data)>MAX_UPLOAD_BYTES: raise HTTPException(413,"File too large")
    signatures={"application/pdf":b"%PDF-","image/png":b"\x89PNG\r\n\x1a\n","image/jpeg":b"\xff\xd8\xff"}
    sig=signatures.get(file.content_type or "")
    if not sig or not data.startswith(sig): raise HTTPException(415,"Unsupported or spoofed file")
    suffix={"application/pdf":".pdf","image/png":".png","image/jpeg":".jpg"}[file.content_type]
    stored=secrets.token_urlsafe(18)+suffix; physical=STORAGE/stored; physical.write_bytes(data)
    try:
        a=Attachment(event_id=None,visit_id=visit.id,original_name=Path(file.filename or "document").name,stored_name=stored,media_type=file.content_type,evidence_type=evidence_type,size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        session.add(a); session.flush(); before=visit_snapshot(visit); recalc_visit_trust(session,visit); visit_audit(session,visit,user.id,"attachment_added",before,visit_snapshot(visit)); session.commit(); return {"id":a.id,"trust_level":visit.trust_level,"sha256":a.sha256}
    except Exception:
        session.rollback(); physical.unlink(missing_ok=True); raise

@app.post("/api/vehicles/{vehicle_id}/share",status_code=201)
def create_share(vehicle_id: str,user: User=Depends(mutation_guard),session: Session=Depends(db)):
    v=own_vehicle(session,user,vehicle_id); current=now()
    for link in session.scalars(select(ShareLink).where(ShareLink.vehicle_id==v.id,ShareLink.revoked_at.is_(None))): link.revoked_at=current
    token=secrets.token_urlsafe(32); link=ShareLink(vehicle_id=v.id,token_hash=sha(token),created_at=current,expires_at=current+timedelta(hours=1)); session.add(link); session.commit()
    return {"id":link.id,"url":f"{PUBLIC_BASE_URL}/p/{token}","expires_at":link.expires_at.isoformat()}

@app.delete("/api/share/{share_id}",status_code=204)
def revoke_share(share_id: str,user: User=Depends(mutation_guard),session: Session=Depends(db)):
    link=session.get(ShareLink,share_id)
    if not link: raise HTTPException(404,"Share link not found")
    own_vehicle(session,user,link.vehicle_id); link.revoked_at=now(); session.commit()

def public_payload(token: str,session: Session):
    link=session.scalar(select(ShareLink).where(ShareLink.token_hash==sha(token)))
    if not link or link.revoked_at or dt_aware(link.expires_at)<=now(): raise HTTPException(404,"Public passport unavailable")
    v=session.get(Vehicle,link.vehicle_id)
    events=session.scalars(select(HistoryEvent).where(HistoryEvent.vehicle_id==v.id,HistoryEvent.is_deleted.is_(False)).order_by(HistoryEvent.event_date.desc()))
    rows=[]
    for e in events:
        row={"event_date":e.event_date.isoformat(),"kind":e.kind,"mileage":e.mileage,"title":e.title,"description":e.description,"trust_level":e.trust_level}
        if e.cost_visible_to_public and e.cost_kopecks is not None: row["cost_rubles"]=e.cost_kopecks/100
        rows.append(row)
    visits=[]
    for visit in session.scalars(select(ServiceVisit).where(ServiceVisit.vehicle_id==v.id,ServiceVisit.is_deleted.is_(False)).order_by(ServiceVisit.visit_date.desc())):
        row={"visit_date":visit.visit_date.isoformat(),"kind":visit.kind,"mileage":visit.mileage,"title":visit.title,"location":visit.location,"description":visit.description,"trust_level":visit.trust_level,"items":[]}
        if visit.total_cost_visible_to_public and visit.total_cost_kopecks is not None:
            row["total_cost_rubles"]=visit.total_cost_kopecks/100
        for item in session.scalars(select(ServiceItem).where(ServiceItem.visit_id==visit.id,ServiceItem.is_deleted.is_(False)).order_by(ServiceItem.item_type,ServiceItem.title)):
            public_item={"item_type":item.item_type,"title":item.title,"description":item.description,"brand":item.brand,"quantity":item.quantity,"unit":item.unit,"cost_status":item.cost_status}
            if visit.total_cost_visible_to_public and item.cost_kopecks is not None:
                public_item["cost_rubles"]=item.cost_kopecks/100
            row["items"].append(public_item)
        visits.append(row)
    return {"vehicle":{"make":v.make,"model":v.model,"trim":v.trim,"year":v.year,"vin":mask_vin(v.vin),"current_mileage":v.current_mileage},"events":rows,"visits":visits,"expires_at":link.expires_at.isoformat()}



def owner_payload(vehicle_id: str, session: Session):
    v = session.get(Vehicle, vehicle_id)
    if not v:
        raise HTTPException(404, "Vehicle not found")
    visits = []
    for visit in session.scalars(select(ServiceVisit).where(ServiceVisit.vehicle_id==v.id,ServiceVisit.is_deleted.is_(False)).order_by(ServiceVisit.visit_date.desc())):
        row = {"visit_date":visit.visit_date.isoformat(),"kind":visit.kind,"mileage":visit.mileage,"title":visit.title,"location":visit.location,"description":visit.description,"trust_level":visit.trust_level,"items":[]}
        if visit.total_cost_kopecks is not None:
            row["total_cost_rubles"] = visit.total_cost_kopecks / 100
        for item in session.scalars(select(ServiceItem).where(ServiceItem.visit_id==visit.id,ServiceItem.is_deleted.is_(False)).order_by(ServiceItem.item_type,ServiceItem.title)):
            row["items"].append({"item_type":item.item_type,"title":item.title,"description":item.description,"brand":item.brand,"part_number":item.part_number,"quantity":item.quantity,"unit":item.unit,"cost_status":item.cost_status,"cost_rubles":item.cost_kopecks/100 if item.cost_kopecks is not None else None})
        visits.append(row)
    return {"vehicle":{"make":v.make,"model":v.model,"trim":v.trim,"year":v.year,"vin":v.vin,"registration_number":v.registration_number,"current_mileage":v.current_mileage},"visits":visits,"events":[]}

@app.get("/api/vehicles/{vehicle_id}/pdf")
def owner_pdf(vehicle_id: str, user: User=Depends(current_user), session: Session=Depends(db)):
    v = own_vehicle(session, user, vehicle_id)
    payload = owner_payload(v.id, session)
    pdf = build_passport_pdf(payload, private=True)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition":"inline; filename=autopassport-private.pdf"})

@app.get("/api/public/{token}/pdf")
def public_pdf(token: str, session: Session=Depends(db)):
    payload = public_payload(token, session)
    public_url = f"{PUBLIC_BASE_URL}/p/{token}"
    pdf = build_passport_pdf(payload, public_url=public_url, private=False)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition":"inline; filename=autopassport-public.pdf"})

@app.post("/api/admin/backups", status_code=201)
def create_admin_backup(x_admin_token: str | None = Header(default=None), session: Session=Depends(db)):
    expected = os.getenv("ADMIN_BACKUP_TOKEN")
    if not expected or not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(403, "Admin backup token required")
    # Touch DB through current session before file copy.
    session.execute(select(Vehicle.id).limit(1)).all()
    return create_backup("0.24.0")

@app.get("/api/admin/backups/{backup_name}/verify")
def verify_admin_backup(backup_name: str, x_admin_token: str | None = Header(default=None)):
    expected = os.getenv("ADMIN_BACKUP_TOKEN")
    if not expected or not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(403, "Admin backup token required")
    safe = Path(backup_name).name
    return verify_backup(BACKUP_DIR / safe)



@app.post("/api/admin/backups/{backup_name}/restore-check")
def restore_check_admin_backup(backup_name: str, x_admin_token: str | None = Header(default=None)):
    expected = os.getenv("ADMIN_BACKUP_TOKEN")
    if not expected or not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(403, "Admin backup token required")
    safe = Path(backup_name).name
    import tempfile, shutil
    target = Path(tempfile.mkdtemp(prefix="autopassport-restore-check-"))
    try:
        result = restore_backup(BACKUP_DIR / safe, target)
        return {"restored": result["restored"], "database_exists": result["database_exists"], "storage_files": result["storage_files"], "backup_sha256": result.get("backup_sha256")}
    finally:
        shutil.rmtree(target, ignore_errors=True)

@app.get("/api/public/{token}")
def public_api(token: str,session: Session=Depends(db)): return public_payload(token,session)
@app.get("/p/{token}",response_class=HTMLResponse)
def public_page(token: str,session: Session=Depends(db)):
    data=public_payload(token,session); v=data["vehicle"]
    event_items="".join(f"<article><b>{e['event_date']} · {e['title']}</b><p>{e['description']}</p><small>{e['trust_level']}{' · '+str(e['mileage'])+' км' if e['mileage'] else ''}</small></article>" for e in data["events"])
    visit_items=""
    for visit in data.get("visits",[]):
        inner="".join(f"<li>{i['title']} <small>{i['cost_status']}</small></li>" for i in visit.get("items",[]))
        cost=f" · {visit['total_cost_rubles']} ₽" if 'total_cost_rubles' in visit else ""
        visit_items += f"<article><b>{visit['visit_date']} · {visit['title']}</b><p>{visit['description']}</p><ul>{inner}</ul><small>{visit['trust_level']}{' · '+str(visit['mileage'])+' км' if visit['mileage'] else ''}{cost}</small></article>"
    return f"<!doctype html><meta name='viewport' content='width=device-width'><title>AutoPassport</title><style>body{{font-family:system-ui;max-width:760px;margin:auto;padding:20px;background:#f4f6f8}}header,article{{background:white;padding:18px;border-radius:16px;margin:12px 0}}small{{color:#667085}}</style><header><h1>{v['make']} {v['model']} {v['year']}</h1><p>VIN: {v['vin']} · {v['current_mileage']} км</p></header>{visit_items}{event_items}"
