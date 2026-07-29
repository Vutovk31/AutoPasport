const ALLOWED_MEDIA_TYPES = new Set(['application/pdf', 'image/jpeg', 'image/png']);
let stagedFile = null;
let previewUrl = null;

function csrfToken() {
  return decodeURIComponent((document.cookie.split('; ').find(value => value.startsWith('autopassport_csrf=')) || '=').split('=')[1]);
}

function selectedVehicleId() {
  return document.querySelector('.vehicle-card.active[data-id]')?.dataset.id || null;
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  if (value < 1024) return `${value} Б`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} КБ`;
  return `${(value / 1024 ** 2).toFixed(1)} МБ`;
}

function setStatus(message, state = '') {
  const status = document.querySelector('#scanStatus');
  if (!status) return;
  status.className = `scan-status${state ? ` ${state}` : ''}`;
  status.textContent = message;
}

function clearPreviewUrl() {
  if (!previewUrl) return;
  URL.revokeObjectURL(previewUrl);
  previewUrl = null;
}

function ensureReviewPanel() {
  let panel = document.querySelector('#scanReviewPanel');
  if (panel) return panel;

  const scanCard = document.querySelector('.scan-card');
  const manualButton = document.querySelector('#scanToManual');
  if (!scanCard || !manualButton) return null;

  panel = document.createElement('section');
  panel.id = 'scanReviewPanel';
  panel.className = 'scan-review-panel';
  panel.hidden = true;
  panel.setAttribute('aria-live', 'polite');
  panel.innerHTML = `
    <div id="scanPreview" class="scan-preview" aria-label="Предпросмотр документа"></div>
    <div class="scan-review-copy">
      <strong id="scanReviewName"></strong>
      <small id="scanReviewMeta"></small>
      <p>Проверьте, что документ читается и выбран правильный тип. До подтверждения файл не отправляется.</p>
    </div>
    <div class="scan-review-actions">
      <button id="confirmScanUpload" type="button">Загрузить документ</button>
      <button id="cancelScanUpload" type="button" class="secondary">Выбрать другой</button>
    </div>`;
  scanCard.insertBefore(panel, manualButton);

  panel.querySelector('#confirmScanUpload').addEventListener('click', uploadStagedFile);
  panel.querySelector('#cancelScanUpload').addEventListener('click', resetStagedFile);
  return panel;
}

function resetStagedFile() {
  stagedFile = null;
  clearPreviewUrl();
  const input = document.querySelector('#scanFile');
  if (input) input.value = '';
  const panel = ensureReviewPanel();
  if (panel) panel.hidden = true;
  const startButton = document.querySelector('#startScan');
  if (startButton) startButton.textContent = 'Сфотографировать / загрузить';
  setStatus('Выберите чек, заказ-наряд, акт, диагностику или смету.');
}

function stageFile(file) {
  const panel = ensureReviewPanel();
  if (!panel) return;

  if (!ALLOWED_MEDIA_TYPES.has(file.type)) {
    resetStagedFile();
    setStatus('Поддерживаются PDF, JPEG и PNG.', 'error');
    return;
  }

  stagedFile = file;
  clearPreviewUrl();
  const preview = panel.querySelector('#scanPreview');
  if (file.type.startsWith('image/')) {
    previewUrl = URL.createObjectURL(file);
    preview.innerHTML = `<img src="${previewUrl}" alt="Предпросмотр выбранного документа">`;
  } else {
    preview.innerHTML = '<div class="scan-pdf-preview" aria-hidden="true">PDF</div>';
  }

  panel.querySelector('#scanReviewName').textContent = file.name;
  panel.querySelector('#scanReviewMeta').textContent = `${file.type} · ${formatBytes(file.size)}`;
  panel.hidden = false;
  const startButton = document.querySelector('#startScan');
  if (startButton) startButton.textContent = 'Переснять / выбрать другой';
  setStatus('Документ выбран. Проверьте предпросмотр перед загрузкой.');
}

async function uploadStagedFile() {
  const vehicleId = selectedVehicleId();
  if (!vehicleId) {
    setStatus('Сначала добавьте или выберите автомобиль.', 'error');
    return;
  }
  if (!stagedFile) {
    setStatus('Сначала сфотографируйте или выберите документ.', 'error');
    return;
  }

  const documentType = document.querySelector('#documentType')?.value || 'receipt';
  const body = new FormData();
  body.append('document_type', documentType);
  body.append('file', stagedFile);

  const confirmButton = document.querySelector('#confirmScanUpload');
  const cancelButton = document.querySelector('#cancelScanUpload');
  if (confirmButton) confirmButton.disabled = true;
  if (cancelButton) cancelButton.disabled = true;
  setStatus(`Загружаем ${stagedFile.name}…`);

  try {
    const response = await fetch(`/api/vehicles/${encodeURIComponent(vehicleId)}/documents`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRF-Token': csrfToken() },
      body,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof payload.detail === 'string' ? payload.detail : `Ошибка HTTP ${response.status}`;
      throw new Error(detail);
    }

    const uploadedName = payload.original_name || stagedFile.name;
    resetStagedFile();
    setStatus(`${uploadedName} загружен во входящие документы.`, 'success');
    document.querySelector('#refreshDocuments')?.click();
  } catch (error) {
    setStatus(`Не удалось загрузить документ: ${error.message}`, 'error');
  } finally {
    if (confirmButton) confirmButton.disabled = false;
    if (cancelButton) cancelButton.disabled = false;
  }
}

function installScanReview() {
  ensureReviewPanel();

  document.addEventListener('click', event => {
    const startButton = event.target.closest('#startScan');
    if (!startButton) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (!selectedVehicleId()) {
      setStatus('Сначала добавьте или выберите автомобиль.', 'error');
      return;
    }
    document.querySelector('#scanFile')?.click();
  }, true);

  document.addEventListener('change', event => {
    if (event.target.id !== 'scanFile') return;
    event.stopImmediatePropagation();
    const file = event.target.files?.[0];
    if (!file) {
      resetStagedFile();
      return;
    }
    stageFile(file);
  }, true);
}

const style = document.createElement('style');
style.textContent = `
  .scan-review-panel{margin:14px 0 4px;padding:12px;border:1px solid #cfe4dd;border-radius:18px;background:#f8fcfa;text-align:left}
  .scan-preview{min-height:150px;border-radius:14px;overflow:hidden;background:#eaf1ee;display:grid;place-items:center}
  .scan-preview img{display:block;width:100%;max-height:320px;object-fit:contain;background:#101714}
  .scan-pdf-preview{width:78px;height:96px;border-radius:12px;background:#fff;color:#b42318;border:1px solid #e4cbc8;display:grid;place-items:center;font-weight:900;box-shadow:0 8px 18px rgba(17,39,32,.1)}
  .scan-review-copy{padding:12px 2px 4px}
  .scan-review-copy strong,.scan-review-copy small{display:block;overflow-wrap:anywhere}
  .scan-review-copy small{margin-top:4px;color:#6b7a76}
  .scan-review-copy p{margin:10px 0 0}
  .scan-review-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .scan-review-actions button{margin-top:8px}
  @media(max-width:360px){.scan-review-actions{grid-template-columns:1fr}}
`;
document.head.append(style);

setTimeout(installScanReview, 0);
