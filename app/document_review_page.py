"""Owner-only mobile review screen for document AI drafts.

The page reads and updates a reviewable draft through the existing API. Vehicle
history changes only after a separate, explicit owner confirmation action.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DocumentAIDraft, DocumentInboxDocument, User
from .security import current_user, db


router = APIRouter(tags=["document-review"])


@router.get("/documents/{document_id}/review", response_class=HTMLResponse)
def document_review_page(
    document_id: str,
    user: User = Depends(current_user),
    session: Session = Depends(db),
):
    """Return the owner review screen with explicit save and confirm actions."""

    document = session.get(DocumentInboxDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    if document.owner_id != user.id:
        raise HTTPException(403, "Forbidden")

    draft = session.scalar(
        select(DocumentAIDraft).where(
            DocumentAIDraft.document_id == document.id,
            DocumentAIDraft.owner_id == user.id,
        )
    )
    if draft is None:
        raise HTTPException(404, "Draft not found")
    if document.status != "needs_review" or draft.status != "needs_review":
        raise HTTPException(409, "Draft is not available for review")

    document_id_json = json.dumps(document.id)
    document_name_json = json.dumps(document.original_name, ensure_ascii=False)
    return HTMLResponse(
        f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#0f6b5a">
  <title>Проверка документа · AutoPassport</title>
  <style>
    *{{box-sizing:border-box}} body{{margin:0;background:#eaf5f1;color:#17332d;font:16px/1.45 system-ui,-apple-system,sans-serif}}
    main{{width:min(100%,520px);min-height:100vh;margin:auto;padding:18px 16px 38px}}
    header{{display:flex;align-items:center;gap:12px;margin-bottom:16px}} .mark{{width:42px;height:42px;border-radius:14px;background:#0f6b5a;color:#fff;display:grid;place-items:center;font-weight:900}}
    .eyebrow{{margin:0;color:#0f6b5a;font-size:.78rem;font-weight:900;text-transform:uppercase;letter-spacing:.08em}} h1{{margin:3px 0 0;font-size:1.45rem}}
    .card{{background:#fff;border:1px solid #dce9e5;border-radius:22px;padding:18px;box-shadow:0 8px 30px rgba(15,107,90,.07);margin-bottom:14px}}
    .status{{display:inline-flex;padding:6px 10px;border-radius:999px;background:#fff4d6;color:#835b00;font-weight:800;font-size:.8rem}}
    label{{display:grid;gap:6px;margin:13px 0;font-weight:800}} input,textarea{{width:100%;border:1px solid #cbdcd7;border-radius:14px;padding:12px;font:inherit;background:#fbfdfc}} textarea{{min-height:100px;resize:vertical}}
    small{{display:block;color:#667085;font-weight:500}} .confidence{{font-size:.78rem;color:#667085}}
    button,a{{width:100%;border:0;border-radius:15px;padding:13px 16px;font:inherit;font-weight:900;text-align:center;text-decoration:none;cursor:pointer}}
    button{{background:#0f6b5a;color:#fff}} button:disabled{{opacity:.55}} .confirm{{margin-top:10px;background:#17332d}} a{{display:block;background:#fff;color:#0f6b5a;border:1px solid #bad3cb;margin-top:10px}}
    .message{{min-height:24px;margin:10px 0 0;font-weight:800}} .error{{color:#b42318}} .success{{color:#0f6b5a}}
    .notice{{background:#fff9e8;border-color:#f0d58a}} .confirm-notice{{margin:14px 0;padding:12px;border-radius:14px;background:#f4f7f6;color:#344f48;font-size:.9rem}}
    .items{{display:grid;gap:10px}} .item{{padding:12px;border:1px solid #dce9e5;border-radius:14px;background:#fbfdfc}}
  </style>
</head>
<body>
<main>
  <header><div class="mark">✓</div><div><p class="eyebrow">AutoPassport</p><h1>Проверка документа</h1></div></header>
  <section class="card notice"><span class="status">Требует проверки</span><h2 id="documentName"></h2><p>Проверьте распознанные данные. До явного подтверждения история автомобиля не изменяется.</p></section>
  <form id="reviewForm" class="card">
    <label>Дата визита <input name="visit_date" type="date"><small class="confidence" data-confidence="visit_date"></small></label>
    <label>Пробег, км <input name="mileage" type="number" min="0"><small class="confidence" data-confidence="mileage"></small></label>
    <label>Сервис / мастер <input name="service_name"><small class="confidence" data-confidence="service_name"></small></label>
    <label>Общая сумма, ₽ <input name="total_cost_rubles" type="number" min="0" step="0.01"><small class="confidence" data-confidence="total_cost_rubles"></small></label>
    <label>Название визита <input name="title"><small class="confidence" data-confidence="title"></small></label>
    <label>Извлечённый текст <textarea name="extracted_text"></textarea></label>
    <section><p class="eyebrow">Найденные позиции</p><div id="items" class="items"></div></section>
    <button id="save" type="submit">Сохранить исправления</button>
    <div class="confirm-notice"><strong>Подтверждение создаст запись в истории.</strong><br>Будет создан сервисный визит, а исходный документ станет его подтверждением.</div>
    <button id="confirm" class="confirm" type="button">Подтвердить и добавить в историю</button>
    <p id="message" class="message" role="status"></p>
    <a id="homeLink" href="/">Вернуться в AutoPassport</a>
  </form>
</main>
<script>
const documentId = {document_id_json};
const documentName = {document_name_json};
const form = document.querySelector('#reviewForm');
const message = document.querySelector('#message');
const saveButton = document.querySelector('#save');
const confirmButton = document.querySelector('#confirm');
let draft = null;
let confirmed = false;

function csrf() {{
  return decodeURIComponent((document.cookie.split('; ').find(x => x.startsWith('autopassport_csrf=')) || '=').split('=')[1]);
}}
function confidenceLabel(value) {{
  if (typeof value !== 'number') return 'Уверенность не указана';
  return `Уверенность распознавания: ${{Math.round(value * 100)}}%`;
}}
function escapeHtml(value) {{
  return String(value ?? '').replace(/[&<>'"]/g, character => ({{'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}})[character]);
}}
function renderItems(items) {{
  const root = document.querySelector('#items');
  if (!Array.isArray(items) || !items.length) {{ root.innerHTML = '<small>Позиции не распознаны.</small>'; return; }}
  root.innerHTML = items.map((item, index) => `<div class="item"><strong>${{index + 1}}. ${{escapeHtml(item.title || 'Без названия')}}</strong><small>${{escapeHtml(item.type || item.item_type || '')}}${{item.brand ? ' · ' + escapeHtml(item.brand) : ''}}${{item.cost_rubles != null ? ' · ' + escapeHtml(item.cost_rubles) + ' ₽' : ''}}</small></div>`).join('');
}}
async function request(url, options={{}}) {{
  const method = (options.method || 'GET').toUpperCase();
  const headers = {{...(options.headers || {{}})}};
  if (!['GET','HEAD'].includes(method)) headers['X-CSRF-Token'] = csrf();
  const response = await fetch(url, {{credentials:'same-origin', ...options, headers}});
  const body = await response.json().catch(() => ({{}}));
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `Ошибка HTTP ${{response.status}}`);
  return body;
}}
function fill(data) {{
  draft = data;
  const fields = data.proposed_fields || {{}};
  document.querySelector('#documentName').textContent = documentName;
  for (const name of ['visit_date','mileage','service_name','total_cost_rubles','title']) {{
    form.elements[name].value = fields[name] ?? '';
    document.querySelector(`[data-confidence="${{name}}"]`).textContent = confidenceLabel(data.confidence?.[name]);
  }}
  form.elements.extracted_text.value = data.extracted_text || '';
  renderItems(fields.items);
}}
function proposedFieldsFromForm() {{
  const proposed = {{...(draft?.proposed_fields || {{}})}};
  for (const name of ['visit_date','service_name','title']) proposed[name] = form.elements[name].value.trim() || null;
  proposed.mileage = form.elements.mileage.value ? Number(form.elements.mileage.value) : null;
  proposed.total_cost_rubles = form.elements.total_cost_rubles.value ? Number(form.elements.total_cost_rubles.value) : null;
  if (proposed.total_cost_rubles != null && !proposed.total_cost_status) proposed.total_cost_status = 'known';
  return proposed;
}}
async function saveDraft() {{
  const updated = await request(`/api/documents/${{documentId}}/draft/review`, {{
    method:'PATCH',
    headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{extracted_text:form.elements.extracted_text.value,proposed_fields:proposedFieldsFromForm()}})
  }});
  fill(updated);
  return updated;
}}
function setBusy(value) {{
  saveButton.disabled = value;
  confirmButton.disabled = value || confirmed;
}}
form.addEventListener('submit', async event => {{
  event.preventDefault();
  setBusy(true);
  message.className = 'message'; message.textContent = 'Сохраняем исправления…';
  try {{
    await saveDraft();
    message.className = 'message success'; message.textContent = 'Исправления сохранены в черновик. История автомобиля не изменена.';
  }} catch (error) {{ message.className = 'message error'; message.textContent = `Не удалось сохранить: ${{error.message}}`; }}
  finally {{ setBusy(false); }}
}});
confirmButton.addEventListener('click', async () => {{
  if (confirmed) return;
  const approved = window.confirm('Создать сервисный визит из проверенных данных и добавить его в историю автомобиля?');
  if (!approved) return;
  setBusy(true);
  message.className = 'message'; message.textContent = 'Сохраняем исправления и создаём визит…';
  try {{
    await saveDraft();
    const result = await request(`/api/documents/${{documentId}}/draft/confirm`, {{method:'POST'}});
    confirmed = true;
    form.querySelectorAll('input,textarea').forEach(element => element.disabled = true);
    saveButton.hidden = true;
    confirmButton.disabled = true;
    confirmButton.textContent = 'Добавлено в историю';
    message.className = 'message success';
    message.textContent = `Сервисный визит создан. Документ подтверждён. ID визита: ${{result.visit_id}}`;
    document.querySelector('#homeLink').textContent = 'Открыть историю автомобиля';
    document.querySelector('#homeLink').href = '/#history';
  }} catch (error) {{
    message.className = 'message error';
    message.textContent = `Не удалось подтвердить документ: ${{error.message}}`;
  }} finally {{ setBusy(false); }}
}});
request(`/api/documents/${{documentId}}/draft`).then(fill).catch(error => {{ message.className='message error'; message.textContent=`Не удалось загрузить черновик: ${{error.message}}`; form.querySelectorAll('input,textarea,button').forEach(x=>x.disabled=true); }});
</script>
</body></html>"""
    )
