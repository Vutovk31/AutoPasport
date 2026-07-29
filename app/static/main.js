const $ = selector => document.querySelector(selector);
let vehicleId = null;
let garageRows = [];
let inboxDocuments = [];

const DOCUMENT_TYPE_LABELS = {
  receipt: 'Чек',
  work_order: 'Заказ-наряд',
  service_act: 'Акт выполненных работ',
  diagnostic_report: 'Диагностический отчёт',
  estimate: 'Смета',
};

const DOCUMENT_STATUS_LABELS = {
  uploaded: 'Загружен, ожидает обработки',
  processing: 'Обрабатывается',
  needs_review: 'Требует проверки',
  confirmed: 'Подтверждён',
  failed: 'Ошибка обработки',
  archived: 'В архиве',
};

function csrf() {
  return decodeURIComponent((document.cookie.split('; ').find(x => x.startsWith('autopassport_csrf=')) || '=').split('=')[1]);
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function errorMessage(body, status) {
  const detail = body?.detail;
  const code = typeof detail === 'object' ? detail.code : body?.code;
  if (code === 'owner_attachment_quota_exceeded') return 'Достигнут лимит количества документов. Удалите ненужные вложения.';
  if (code === 'owner_storage_quota_exceeded') return 'Недостаточно места в хранилище. Удалите ненужные вложения.';
  if (code === 'vehicle_share_link_quota_exceeded') return 'Для этого автомобиля уже действует максимальное число публичных ссылок.';
  if (code === 'owner_share_link_quota_exceeded') return 'Достигнут общий лимит активных публичных ссылок.';
  return typeof detail === 'string' ? detail : `Ошибка HTTP ${status}`;
}

async function api(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = { ...(options.headers || {}) };
  if (!['GET', 'HEAD'].includes(method)) headers['X-CSRF-Token'] = csrf();
  const response = await fetch(url, { credentials: 'same-origin', ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(errorMessage(body, response.status));
  }
  return response.status === 204 ? null : response.json();
}

function setView(viewName) {
  document.querySelectorAll('[data-view-panel]').forEach(panel => {
    panel.hidden = panel.dataset.viewPanel !== viewName;
  });
  document.querySelectorAll('.bottom-nav [data-view]').forEach(button => {
    button.classList.toggle('active', button.dataset.view === viewName);
  });
  if (viewName === 'scan') refreshDocumentInbox();
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  if (value < 1024) return `${value} Б`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} КБ`;
  return `${(value / 1024 ** 2).toFixed(1)} МБ`;
}

function money(value) {
  return value === null || value === undefined || value === '' ? '' : `${Number(value).toLocaleString('ru-RU')} ₽`;
}

function maskVin(vin) {
  const value = String(vin || '').trim().toUpperCase();
  if (!value) return 'VIN не указан';
  if (value.length < 12) return value;
  return `${value.slice(0, 7)}••••••${value.slice(-4)}`;
}

function renderScanVehicleContext(vehicle = null) {
  const selected = $('#scanVehicleSelected');
  const empty = $('#scanVehicleEmpty');
  const uploadButton = $('#startScan');
  if (!selected || !empty) return;

  selected.hidden = !vehicle;
  empty.hidden = Boolean(vehicle);
  if (uploadButton) uploadButton.disabled = !vehicle;
  if (!vehicle) return;

  $('#scanVehicleName').textContent = `${vehicle.make || ''} ${vehicle.model || ''}`.trim() || 'Выбранный автомобиль';
  const vehicleYear = vehicle.year ? ` · ${vehicle.year}` : '';
  const mileage = Number(vehicle.current_mileage || 0).toLocaleString('ru-RU');
  $('#scanVehicleMeta').textContent = `${maskVin(vehicle.vin)}${vehicleYear} · ${mileage} км`;
}

function renderStorage(usage) {
  $('#storageAttachments').textContent = `${usage.attachments} из ${usage.max_attachments}`;
  $('#storageBytes').textContent = `${formatBytes(usage.bytes_used)} из ${formatBytes(usage.max_bytes)}`;
  $('#attachmentsProgress').value = usage.attachments_percent;
  $('#bytesProgress').value = usage.bytes_percent;
  $('#storageSummary').textContent = `Осталось ${usage.attachments_remaining} документов и ${formatBytes(usage.bytes_remaining)}`;
  const used = Math.max(usage.attachments_percent, usage.bytes_percent);
  const warning = $('#storageWarning');
  warning.hidden = used < 80;
  warning.className = used >= 95 ? 'warning danger' : 'warning';
  warning.textContent = used >= 95
    ? 'Хранилище почти заполнено. Перед новой загрузкой освободите место.'
    : 'Использовано более 80% хранилища.';
}

async function refreshStorage() {
  try {
    renderStorage(await api('/api/me/storage'));
  } catch (error) {
    $('#storageSummary').textContent = `Не удалось получить данные: ${error.message}`;
  }
}

function renderShares(usage) {
  const active = Number(usage.active_links || 0);
  const maximum = Math.max(Number(usage.max_active_links || 0), 1);
  const remaining = Math.max(Number(usage.remaining_links || 0), 0);
  const percent = Math.min(100, Math.round((active / maximum) * 100));
  $('#shareLinks').textContent = `${active} из ${usage.max_active_links}`;
  $('#shareProgress').value = percent;
  $('#shareSummary').textContent = `Можно создать ещё ${remaining}`;
  const warning = $('#shareWarning');
  warning.hidden = percent < 80;
  warning.className = percent >= 100 ? 'warning danger' : 'warning';
  warning.textContent = percent >= 100
    ? 'Лимит активных публичных ссылок исчерпан.'
    : 'Использовано не менее 80% лимита публичных ссылок.';
}

function formatRemaining(seconds) {
  const value = Math.max(0, Number(seconds || 0));
  const minutes = Math.ceil(value / 60);
  if (minutes < 60) return `${minutes} мин.`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} ч ${rest} мин.` : `${hours} ч`;
}

function renderActiveShareLinks(payload) {
  const links = payload.links || [];
  const container = $('#activeShareList');
  if (!links.length) {
    container.innerHTML = '<p>Активных публичных ссылок нет.</p>';
    return;
  }
  container.innerHTML = links.map(link => {
    const vehicle = link.vehicle || {};
    const name = `${escapeHtml(vehicle.make)} ${escapeHtml(vehicle.model)} ${escapeHtml(vehicle.year)}`.trim();
    const plate = vehicle.registration_number ? ` · ${escapeHtml(vehicle.registration_number)}` : '';
    return `<article class="share-item"><div><strong>${name}</strong><small>${plate} · осталось ${formatRemaining(link.seconds_remaining)}</small></div><button type="button" class="revoke-share secondary" data-id="${escapeHtml(link.id)}">Отозвать</button></article>`;
  }).join('');
  document.querySelectorAll('.revoke-share').forEach(button => {
    button.onclick = async () => {
      button.disabled = true;
      try {
        await api(`/api/share/${button.dataset.id}`, { method: 'DELETE' });
        await refreshShares();
      } catch (error) {
        alert(error.message);
        button.disabled = false;
      }
    };
  });
}

async function refreshShares() {
  try {
    const [usage, list] = await Promise.all([
      api('/api/me/shares'),
      api('/api/me/shares/list'),
    ]);
    renderShares(usage);
    renderActiveShareLinks(list);
  } catch (error) {
    $('#shareSummary').textContent = `Не удалось получить данные: ${error.message}`;
    $('#activeShareList').innerHTML = '<p>Список ссылок недоступен.</p>';
  }
}

function renderGarageVehicles(rows) {
  $('#garageCount').textContent = `${rows.length}`;
  if (!rows.length) {
    $('#garage').innerHTML = '<button type="button" class="vehicle-card" data-view="add"><div class="vehicle-card-top"><div class="car-icon">＋</div><div><small>Автомобиль</small><h2>Добавьте авто</h2><small>VIN, пробег и базовые данные</small></div></div></button>';
    renderScanVehicleContext();
    return;
  }
  $('#garage').innerHTML = rows.map(v => `
    <button type="button" class="vehicle-card ${String(v.id) === String(vehicleId) ? 'active' : ''}" data-id="${escapeHtml(v.id)}">
      <div class="vehicle-card-top">
        <div class="car-icon">▣</div>
        <div>
          <small>Автомобиль</small>
          <h2>${escapeHtml(v.make)} ${escapeHtml(v.model)}</h2>
          <small>${escapeHtml(v.trim || '')} · ${escapeHtml(v.year || '')}</small>
        </div>
      </div>
      <div class="vehicle-meta">
        <div><span>VIN</span><strong>${escapeHtml(maskVin(v.vin))}</strong></div>
        <div><span>Текущий пробег</span><strong>${Number(v.current_mileage || 0).toLocaleString('ru-RU')} км</strong></div>
      </div>
    </button>
  `).join('');
  document.querySelectorAll('.vehicle-card[data-id]').forEach(button => button.onclick = () => openVehicle(button.dataset.id));
  renderScanVehicleContext(rows.find(vehicle => String(vehicle.id) === String(vehicleId)) || null);
}

async function garage() {
  garageRows = await api('/api/vehicles');
  $('#app').hidden = false;
  $('#auth').hidden = true;
  renderGarageVehicles(garageRows);
  await Promise.all([refreshStorage(), refreshShares()]);
  if (!vehicleId && garageRows[0]) await openVehicle(garageRows[0].id, { stayOnCurrentView: true });
  if (!garageRows.length) setView('add');
}

function renderVisitCard(v) {
  const items = (v.items || []).map(i => `<li>${escapeHtml(i.title)} — ${escapeHtml(i.cost_status)}${i.cost_rubles ? ` · ${money(i.cost_rubles)}` : ''}</li>`).join('');
  return `
    <article class="card timeline-card">
      <span class="tile-icon repair">🔧</span>
      <div>
        <small>${escapeHtml(v.visit_date)} · ${escapeHtml(v.trust_level)} · rev.${escapeHtml(v.revision)}</small>
        <h3>${escapeHtml(v.title)}</h3>
        <p>${escapeHtml(v.location || '')}</p>
        <p>${v.mileage ? Number(v.mileage).toLocaleString('ru-RU') + ' км' : ''} ${money(v.total_cost_rubles)}</p>
        ${items ? `<ul>${items}</ul>` : ''}
      </div>
      <span>›</span>
      <button class="delete-visit" data-id="${escapeHtml(v.id)}" type="button">Скрыть визит</button>
    </article>
  `;
}

function renderEventCard(e) {
  return `
    <article class="card timeline-card">
      <span class="tile-icon mileage">⌁</span>
      <div>
        <small>${escapeHtml(e.event_date)} · ${escapeHtml(e.trust_level)} · rev.${escapeHtml(e.revision)}</small>
        <h3>${escapeHtml(e.title)}</h3>
        <p>${escapeHtml(e.description || '')}</p>
        <p>${e.mileage ? Number(e.mileage).toLocaleString('ru-RU') + ' км' : ''}</p>
      </div>
      <span>›</span>
      <button class="delete" data-id="${escapeHtml(e.id)}" type="button">Скрыть событие</button>
    </article>
  `;
}

function renderArchiveSummary(data) {
  const visits = data.visits || [];
  const events = data.events || [];
  const itemCount = visits.reduce((sum, visit) => sum + (visit.items || []).length, 0);
  const attachedCount = visits.reduce((sum, visit) => sum + (visit.attachments || []).length, 0)
    + events.reduce((sum, event) => sum + (event.attachments || []).length, 0);
  const documentCount = attachedCount + inboxDocuments.length;
  $('#repairCount').textContent = `${visits.length} записей`;
  $('#partsCount').textContent = `${itemCount} записей`;
  $('#mileageCount').textContent = `${visits.filter(v => v.mileage).length + events.filter(e => e.mileage).length} отметки`;
  $('#documentSummary').textContent = documentCount ? `${documentCount} документов добавлено` : 'Документы пока не добавлены';
}

function renderLatestRecord(data) {
  const visits = data.visits || [];
  const events = data.events || [];
  const latestVisit = visits[0] ? { type: 'visit', date: visits[0].visit_date, mileage: visits[0].mileage, title: visits[0].title } : null;
  const latestEvent = events[0] ? { type: 'event', date: events[0].event_date, mileage: events[0].mileage, title: events[0].title } : null;
  const latest = [latestVisit, latestEvent].filter(Boolean).sort((a, b) => String(b.date).localeCompare(String(a.date)))[0];
  if (!latest) {
    $('#latestRecord').innerHTML = 'Записей пока нет. Добавьте первый ремонт, ТО или документ.';
    return;
  }
  $('#latestRecord').innerHTML = `<article class="timeline-card"><span class="tile-icon repair">🔧</span><div><small>${escapeHtml(latest.date)}${latest.mileage ? ` · ${Number(latest.mileage).toLocaleString('ru-RU')} км` : ''}</small><h3>${escapeHtml(latest.title)}</h3></div><span>›</span></article>`;
}

function ensureDocumentInboxUi() {
  const scanCard = document.querySelector('.scan-card');
  if (!scanCard || $('#documentType')) return;
  const typeSelect = document.createElement('select');
  typeSelect.id = 'documentType';
  typeSelect.setAttribute('aria-label', 'Тип документа');
  typeSelect.innerHTML = Object.entries(DOCUMENT_TYPE_LABELS)
    .map(([value, label]) => `<option value="${value}">${label}</option>`)
    .join('');
  scanCard.insertBefore(typeSelect, $('#scanFile'));

  const inbox = document.createElement('section');
  inbox.className = 'document-inbox card';
  inbox.innerHTML = '<div class="section-title-row"><div><p class="eyebrow">Входящие документы</p><h2>Ожидают обработки</h2></div><button id="refreshDocuments" type="button" class="text-button">Обновить</button></div><div id="documentInboxList"><p class="muted-card">Выберите автомобиль.</p></div>';
  document.querySelector('[data-view-panel="scan"]')?.append(inbox);
  $('#refreshDocuments').onclick = refreshDocumentInbox;

  const style = document.createElement('style');
  style.textContent = `
    #documentType{width:100%;margin:8px 0 12px;background:#fff}
    .document-inbox{margin-top:16px}
    .document-inbox-list{display:grid;gap:10px}
    .document-inbox-item{display:grid;grid-template-columns:42px 1fr;gap:12px;align-items:center;padding:12px;border:1px solid #dfe8e5;border-radius:16px;background:#fff}
    .document-inbox-item .doc-icon{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;background:#e7f3ef;color:#0f6b5a;font-weight:900}
    .document-inbox-item h3{margin:2px 0 4px;font-size:1rem}
    .document-inbox-item small{display:block;color:#667085}
    .document-status{display:inline-flex;margin-top:7px;padding:5px 9px;border-radius:999px;background:#fff4d6;color:#835b00;font-size:.78rem;font-weight:800}
    .document-status.confirmed{background:#e7f3ef;color:#0f6b5a}
    .document-status.failed{background:#fee4e2;color:#b42318}
    .scan-status.success{color:#0f6b5a;font-weight:800}
    .scan-status.error{color:#b42318;font-weight:800}
  `;
  document.head.append(style);
}

function renderDocumentInbox(documents) {
  const container = $('#documentInboxList');
  if (!container) return;
  if (!vehicleId) {
    container.innerHTML = '<p class="muted-card">Сначала выберите или добавьте автомобиль.</p>';
    return;
  }
  if (!documents.length) {
    container.innerHTML = '<p class="muted-card">Загруженных документов пока нет.</p>';
    return;
  }
  container.innerHTML = `<div class="document-inbox-list">${documents.map(document => {
    const statusClass = document.status === 'confirmed' ? 'confirmed' : document.status === 'failed' ? 'failed' : '';
    const created = document.created_at ? new Date(document.created_at).toLocaleString('ru-RU') : '';
    return `<article class="document-inbox-item">
      <div class="doc-icon">▤</div>
      <div>
        <small>${escapeHtml(DOCUMENT_TYPE_LABELS[document.document_type] || document.document_type)} · ${formatBytes(document.size_bytes)}</small>
        <h3>${escapeHtml(document.original_name)}</h3>
        <small>${escapeHtml(created)}</small>
        <span class="document-status ${statusClass}">${escapeHtml(DOCUMENT_STATUS_LABELS[document.status] || document.status)}</span>
      </div>
    </article>`;
  }).join('')}</div>`;
}

async function refreshDocumentInbox() {
  ensureDocumentInboxUi();
  if (!vehicleId) {
    inboxDocuments = [];
    renderDocumentInbox([]);
    return;
  }
  try {
    const payload = await api(`/api/vehicles/${vehicleId}/documents`);
    inboxDocuments = payload.documents || [];
    renderDocumentInbox(inboxDocuments);
    $('#documentSummary').textContent = inboxDocuments.length
      ? `${inboxDocuments.length} входящих документов`
      : 'Документы пока не добавлены';
  } catch (error) {
    $('#documentInboxList').innerHTML = `<p class="muted-card">Не удалось загрузить список: ${escapeHtml(error.message)}</p>`;
  }
}

async function openVehicle(id, options = {}) {
  vehicleId = id;
  renderGarageVehicles(garageRows);
  const [data] = await Promise.all([
    api(`/api/vehicles/${id}`),
    refreshDocumentInbox(),
  ]);
  $('#detail').hidden = false;
  $('#vehicle').innerHTML = `
    <article class="passport-card">
      <h2>${escapeHtml(data.vehicle.make)} ${escapeHtml(data.vehicle.model)} ${escapeHtml(data.vehicle.year)}</h2>
      <p>${escapeHtml(maskVin(data.vehicle.vin))} · ${escapeHtml(data.vehicle.registration_number || 'без госномера')} · ${Number(data.vehicle.current_mileage || 0).toLocaleString('ru-RU')} км</p>
      <div class="vehicle-meta">
        <div><span>Паспорт</span><strong>Личный архив</strong></div>
        <div><span>Доверие</span><strong>По документам</strong></div>
      </div>
    </article>
  `;
  $('#visits').innerHTML = (data.visits || []).map(renderVisitCard).join('') || '<p class="muted-card card">Визитов пока нет.</p>';
  $('#timeline').innerHTML = (data.events || []).map(renderEventCard).join('') || '<p class="muted-card card">Событий пока нет.</p>';
  renderArchiveSummary(data);
  renderLatestRecord(data);
  document.querySelectorAll('.delete').forEach(button => button.onclick = async () => { await api(`/api/events/${button.dataset.id}`, { method: 'DELETE' }); await openVehicle(id); await refreshStorage(); });
  document.querySelectorAll('.delete-visit').forEach(button => button.onclick = async () => { await api(`/api/visits/${button.dataset.id}`, { method: 'DELETE' }); await openVehicle(id); await refreshStorage(); });
  if (!options.stayOnCurrentView) setView('home');
}

$('#authForm').onsubmit = async event => {
  event.preventDefault();
  const body = new FormData(event.target);
  try {
    await api('/api/auth/login', { method: 'POST', body });
  } catch (_) {
    await api('/api/auth/register', { method: 'POST', body });
  }
  await garage();
  setView('home');
};

$('#vehicleForm').onsubmit = async event => {
  event.preventDefault();
  const vehicle = await api('/api/vehicles', { method: 'POST', body: new FormData(event.target) });
  event.target.reset();
  await garage();
  await openVehicle(vehicle.id);
  setView('home');
};

$('#eventForm').onsubmit = async event => {
  event.preventDefault();
  if (!vehicleId) return alert('Сначала выберите автомобиль.');
  await api(`/api/vehicles/${vehicleId}/events`, { method: 'POST', body: new FormData(event.target) });
  event.target.reset();
  await openVehicle(vehicleId);
  setView('history');
};

$('#visitForm').onsubmit = async event => {
  event.preventDefault();
  if (!vehicleId) return alert('Сначала выберите автомобиль.');
  const f = new FormData(event.target);
  const body = {
    kind: f.get('kind'),
    visit_date: f.get('visit_date'),
    mileage: f.get('mileage') || null,
    title: f.get('title'),
    location: f.get('location'),
    total_cost_rubles: f.get('total_cost_rubles') || null,
    total_cost_status: f.get('total_cost_status'),
    total_cost_visible_to_public: f.get('total_cost_visible_to_public') === 'on',
    items: [{
      item_type: f.get('item_type'),
      title: f.get('item_title'),
      brand: f.get('item_brand'),
      quantity: f.get('item_quantity'),
      unit: f.get('item_unit'),
      cost_rubles: f.get('item_cost_rubles') || null,
      cost_status: f.get('item_cost_status'),
    }],
  };
  await api(`/api/vehicles/${vehicleId}/visits`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  event.target.reset();
  await openVehicle(vehicleId);
  setView('history');
};

$('#share').onclick = async () => {
  if (!vehicleId) return alert('Сначала выберите автомобиль.');
  try {
    const share = await api(`/api/vehicles/${vehicleId}/share`, { method: 'POST' });
    await navigator.clipboard.writeText(share.url).catch(() => {});
    await refreshShares();
    alert(`Ссылка действует 1 час:\n${share.url}`);
  } catch (error) {
    await refreshShares();
    alert(error.message);
  }
};

$('#refreshStorage').onclick = refreshStorage;
$('#refreshShares').onclick = refreshShares;

document.addEventListener('click', event => {
  const trigger = event.target.closest('[data-view]');
  if (!trigger) return;
  const view = trigger.dataset.view;
  if (view === 'passport' && !vehicleId) alert('Сначала добавьте или выберите автомобиль.');
  setView(view);
});

ensureDocumentInboxUi();
const startScan = $('#startScan');
const scanFile = $('#scanFile');
const scanToManual = $('#scanToManual');
const changeScanVehicle = $('#changeScanVehicle');
const scanAddVehicle = $('#scanAddVehicle');
if (startScan && scanFile) startScan.onclick = () => {
  if (!vehicleId) {
    $('#scanStatus').className = 'scan-status error';
    $('#scanStatus').textContent = 'Сначала выберите автомобиль для документа.';
    return;
  }
  scanFile.click();
};
if (scanToManual) scanToManual.onclick = () => setView('add');
if (changeScanVehicle) changeScanVehicle.onclick = () => {
  setView('home');
  requestAnimationFrame(() => document.querySelector('.vehicle-card.active[data-id]')?.focus());
};
if (scanAddVehicle) scanAddVehicle.onclick = () => {
  setView(garageRows.length ? 'home' : 'add');
  requestAnimationFrame(() => {
    const target = garageRows.length
      ? document.querySelector('.vehicle-card[data-id]')
      : document.querySelector('#vehicleForm input[name="vin"]');
    target?.focus();
  });
};
if (scanFile) scanFile.onchange = async () => {
  const file = scanFile.files?.[0];
  const status = $('#scanStatus');
  if (!file) {
    status.className = 'scan-status';
    status.textContent = 'Выберите чек, заказ-наряд, акт, диагностику или смету.';
    return;
  }
  if (!vehicleId) {
    status.className = 'scan-status error';
    status.textContent = 'Сначала добавьте или выберите автомобиль.';
    scanFile.value = '';
    return;
  }
  const documentType = $('#documentType')?.value || 'receipt';
  const body = new FormData();
  body.append('document_type', documentType);
  body.append('file', file);
  startScan.disabled = true;
  status.className = 'scan-status';
  status.textContent = `Загружаем ${file.name}…`;
  try {
    const uploaded = await api(`/api/vehicles/${vehicleId}/documents`, { method: 'POST', body });
    status.className = 'scan-status success';
    status.textContent = `${uploaded.original_name} загружен в архив. Статус: ${DOCUMENT_STATUS_LABELS[uploaded.status]}.`;
    scanFile.value = '';
    await refreshDocumentInbox();
  } catch (error) {
    status.className = 'scan-status error';
    status.textContent = `Не удалось загрузить документ: ${error.message}`;
  } finally {
    startScan.disabled = false;
  }
};

api('/api/me').then(async () => { await garage(); setView('home'); }).catch(() => {});

if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('/service-worker.js').catch(() => {}));
let deferredInstallPrompt = null;
const installButton = $('#installApp');
window.addEventListener('beforeinstallprompt', event => { event.preventDefault(); deferredInstallPrompt = event; if (installButton) installButton.hidden = false; });
if (installButton) installButton.onclick = async () => { if (!deferredInstallPrompt) return; deferredInstallPrompt.prompt(); await deferredInstallPrompt.userChoice.catch(() => null); deferredInstallPrompt = null; installButton.hidden = true; };
const ownerPdfButton = $('#downloadPdf');
if (ownerPdfButton) ownerPdfButton.onclick = () => { if (vehicleId) window.open(`/api/vehicles/${vehicleId}/pdf`, '_blank'); };
