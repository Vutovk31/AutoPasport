"""Owner-only mobile page for a service visit created from a confirmed document."""

from __future__ import annotations

from html import escape

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DocumentInboxDocument, ServiceItem, ServiceVisit, User, Vehicle
from .security import current_user, db


router = APIRouter(tags=["confirmed-visit"])


def _rubles(value: int | None) -> str:
    if value is None:
        return "Не указана"
    rubles = value / 100
    return f"{rubles:,.2f}".replace(",", " ").replace(".00", "") + " ₽"


@router.get("/visits/{visit_id}/confirmed", response_class=HTMLResponse)
def confirmed_visit_page(
    visit_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(db),
):
    """Show the committed visit and its source document to the owning user."""

    visit = session.get(ServiceVisit, visit_id)
    if visit is None or visit.is_deleted:
        raise HTTPException(404, "Service visit not found")

    vehicle = session.get(Vehicle, visit.vehicle_id)
    if vehicle is None:
        raise HTTPException(404, "Vehicle not found")
    if vehicle.owner_id != user.id:
        raise HTTPException(403, "Forbidden")

    document = session.scalar(
        select(DocumentInboxDocument).where(
            DocumentInboxDocument.linked_visit_id == visit.id,
            DocumentInboxDocument.owner_id == user.id,
            DocumentInboxDocument.status == "confirmed",
        )
    )
    if document is None:
        raise HTTPException(404, "Confirmed source document not found")

    items = list(
        session.scalars(
            select(ServiceItem)
            .where(ServiceItem.visit_id == visit.id, ServiceItem.is_deleted.is_(False))
            .order_by(ServiceItem.item_type, ServiceItem.title)
        )
    )
    item_html = "".join(
        f"<li><strong>{escape(item.title)}</strong>"
        f"<small>{escape(item.item_type)}"
        f"{' · ' + escape(item.brand) if item.brand else ''}"
        f"{' · ' + _rubles(item.cost_kopecks) if item.cost_kopecks is not None else ''}</small></li>"
        for item in items
    ) or "<li><small>Позиции не указаны.</small></li>"

    mileage = f"{visit.mileage:,}".replace(",", " ") + " км" if visit.mileage is not None else "Не указан"
    location = escape(visit.location) if visit.location else "Не указан"
    return HTMLResponse(
        f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0f6b5a"><title>Визит добавлен · AutoPassport</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#eaf5f1;color:#17332d;font:16px/1.45 system-ui,-apple-system,sans-serif}}main{{width:min(100%,520px);min-height:100vh;margin:auto;padding:18px 16px 38px}}.card{{background:#fff;border:1px solid #dce9e5;border-radius:22px;padding:18px;box-shadow:0 8px 30px rgba(15,107,90,.07);margin-bottom:14px}}.mark{{width:48px;height:48px;border-radius:16px;background:#0f6b5a;color:#fff;display:grid;place-items:center;font-size:1.4rem;font-weight:900}}header{{display:flex;align-items:center;gap:12px;margin-bottom:16px}}h1,h2,p{{margin-top:0}}.status{{display:inline-flex;padding:6px 10px;border-radius:999px;background:#dff6ee;color:#0f6b5a;font-weight:900;font-size:.8rem}}dl{{display:grid;grid-template-columns:1fr auto;gap:10px;margin:16px 0}}dt{{color:#667085}}dd{{margin:0;font-weight:800;text-align:right}}ul{{list-style:none;padding:0;margin:0;display:grid;gap:10px}}li{{padding:12px;border:1px solid #dce9e5;border-radius:14px;background:#fbfdfc}}small{{display:block;color:#667085;margin-top:3px}}a{{display:block;border-radius:15px;padding:13px 16px;font-weight:900;text-align:center;text-decoration:none;background:#0f6b5a;color:#fff;margin-top:10px}}a.secondary{{background:#fff;color:#0f6b5a;border:1px solid #bad3cb}}</style></head>
<body><main><header><div class="mark">✓</div><div><span class="status">Добавлено в историю</span><h1>{escape(visit.title)}</h1></div></header>
<section class="card"><h2>{escape(vehicle.make)} {escape(vehicle.model)} · {vehicle.year}</h2><dl><dt>Дата</dt><dd>{visit.visit_date.isoformat()}</dd><dt>Пробег</dt><dd>{mileage}</dd><dt>Сервис / мастер</dt><dd>{location}</dd><dt>Сумма</dt><dd>{_rubles(visit.total_cost_kopecks)}</dd></dl><p>{escape(visit.description) if visit.description else 'Описание не указано.'}</p></section>
<section class="card"><h2>Работы и детали</h2><ul>{item_html}</ul></section>
<section class="card"><h2>Исходный документ</h2><p><strong>{escape(document.original_name)}</strong></p><small>{escape(document.document_type)} · SHA-256: {escape(document.sha256[:12])}…</small><a href="/api/documents/{document.id}/file" target="_blank" rel="noopener">Открыть документ</a></section>
<a href="/">Вернуться в AutoPassport</a><a class="secondary" href="/#history">Открыть всю историю</a></main></body></html>"""
    )
