const $ = selector => document.querySelector(selector);
let vehicleId = null;

function csrf() {
  return decodeURIComponent((document.cookie.split('; ').find(x => x.startsWith('autopassport_csrf=')) || '=').split('=')[1]);
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

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  if (value < 1024) return `${value} Б`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} КБ`;
  return `${(value / 1024 ** 2).toFixed(1)} МБ`;
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

async function refreshShares() {
  try {
    renderShares(await api('/api/me/shares'));
  } catch (error) {
    $('#shareSummary').textContent = `Не удалось получить данные: ${error.message}`;
  }
}

async function garage() {
  const rows = await api('/api/vehicles');
  $('#app').hidden = false;
  $('#auth').hidden = true;
  $('#garage').innerHTML = rows.map(v => `<button class="vehicle" data-id="${v.id}"><b>${v.make} ${v.model}</b><span>${v.current_mileage.toLocaleString('ru-RU')} км</span></button>`).join('') || '<p>Добавьте первый автомобиль.</p>';
  document.querySelectorAll('.vehicle').forEach(button => button.onclick = () => openVehicle(button.dataset.id));
  await Promise.all([refreshStorage(), refreshShares()]);
}

function money(value) { return value === null || value === undefined ? '' : `${Number(value).toLocaleString('ru-RU')} ₽`; }

async function openVehicle(id) {
  vehicleId = id;
  const data = await api(`/api/vehicles/${id}`);
  $('#detail').hidden = false;
  $('#share').hidden = false;
  $('#vehicle').innerHTML = `<h2>${data.vehicle.make} ${data.vehicle.model} ${data.vehicle.year}</h2><p>${data.vehicle.vin} · ${data.vehicle.registration_number || ''} · ${data.vehicle.current_mileage.toLocaleString('ru-RU')} км</p>`;
  $('#visits').innerHTML = (data.visits || []).map(v => `<article class="card"><small>${v.visit_date} · ${v.trust_level} · rev.${v.revision}</small><h3>${v.title}</h3><p>${v.location || ''}</p><p>${v.mileage ? v.mileage.toLocaleString('ru-RU') + ' км' : ''} ${money(v.total_cost_rubles)}</p><ul>${v.items.map(i => `<li>${i.title} — ${i.cost_status}${i.cost_rubles ? ` · ${money(i.cost_rubles)}` : ''}</li>`).join('')}</ul><button class="delete-visit" data-id="${v.id}">Скрыть визит</button></article>`).join('') || '<p>Визитов пока нет.</p>';
  $('#timeline').innerHTML = data.events.map(e => `<article class="card"><small>${e.event_date} · ${e.trust_level} · rev.${e.revision}</small><h3>${e.title}</h3><p>${e.description}</p><p>${e.mileage ? e.mileage.toLocaleString('ru-RU') + ' км' : ''}</p><button class="delete" data-id="${e.id}">Скрыть событие</button></article>`).join('') || '<p>Событий пока нет.</p>';
  document.querySelectorAll('.delete').forEach(button => button.onclick = async () => { await api(`/api/events/${button.dataset.id}`, { method: 'DELETE' }); await openVehicle(id); await refreshStorage(); });
  document.querySelectorAll('.delete-visit').forEach(button => button.onclick = async () => { await api(`/api/visits/${button.dataset.id}`, { method: 'DELETE' }); await openVehicle(id); await refreshStorage(); });
}

$('#authForm').onsubmit = async event => { event.preventDefault(); const body = new FormData(event.target); try { await api('/api/auth/login', { method: 'POST', body }); } catch (_) { await api('/api/auth/register', { method: 'POST', body }); } await garage(); };
$('#vehicleForm').onsubmit = async event => { event.preventDefault(); const vehicle = await api('/api/vehicles', { method: 'POST', body: new FormData(event.target) }); event.target.reset(); await garage(); await openVehicle(vehicle.id); };
$('#eventForm').onsubmit = async event => { event.preventDefault(); await api(`/api/vehicles/${vehicleId}/events`, { method: 'POST', body: new FormData(event.target) }); event.target.reset(); await openVehicle(vehicleId); };
$('#visitForm').onsubmit = async event => { event.preventDefault(); const f = new FormData(event.target); const body = { kind: f.get('kind'), visit_date: f.get('visit_date'), mileage: f.get('mileage') || null, title: f.get('title'), location: f.get('location'), total_cost_rubles: f.get('total_cost_rubles') || null, total_cost_status: f.get('total_cost_status'), total_cost_visible_to_public: f.get('total_cost_visible_to_public') === 'on', items: [{ item_type: f.get('item_type'), title: f.get('item_title'), brand: f.get('item_brand'), quantity: f.get('item_quantity'), unit: f.get('item_unit'), cost_rubles: f.get('item_cost_rubles') || null, cost_status: f.get('item_cost_status') }] }; await api(`/api/vehicles/${vehicleId}/visits`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); event.target.reset(); await openVehicle(vehicleId); };
$('#share').onclick = async () => {
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

api('/api/me').then(garage).catch(() => {});

if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('/service-worker.js').catch(() => {}));
let deferredInstallPrompt = null;
const installButton = $('#installApp');
window.addEventListener('beforeinstallprompt', event => { event.preventDefault(); deferredInstallPrompt = event; if (installButton) installButton.hidden = false; });
if (installButton) installButton.onclick = async () => { if (!deferredInstallPrompt) return; deferredInstallPrompt.prompt(); await deferredInstallPrompt.userChoice.catch(() => null); deferredInstallPrompt = null; installButton.hidden = true; };
const ownerPdfButton = $('#downloadPdf');
if (ownerPdfButton) ownerPdfButton.onclick = () => { if (vehicleId) window.open(`/api/vehicles/${vehicleId}/pdf`, '_blank'); };