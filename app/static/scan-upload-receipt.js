const VIEWABLE_MEDIA_TYPES = new Set(['application/pdf', 'image/jpeg', 'image/png']);
const REVIEW_STATUS = 'needs_review';

function ensureReceiptPanel() {
  let panel = document.querySelector('#scanUploadReceipt');
  if (panel) return panel;

  const scanCard = document.querySelector('.scan-card');
  if (!scanCard) return null;

  panel = document.createElement('section');
  panel.id = 'scanUploadReceipt';
  panel.className = 'scan-upload-receipt';
  panel.hidden = true;
  panel.setAttribute('aria-live', 'polite');
  scanCard.append(panel);
  return panel;
}

function createAction(href, label, className, newTab = false) {
  const link = document.createElement('a');
  link.href = href;
  link.textContent = label;
  link.className = className;
  if (newTab) {
    link.target = '_blank';
    link.rel = 'noopener';
  }
  return link;
}

function renderAcceptedDocument(documentRecord) {
  const panel = ensureReceiptPanel();
  if (!panel || !documentRecord?.id) return;

  panel.replaceChildren();
  panel.dataset.documentId = String(documentRecord.id);
  panel.dataset.vehicleId = String(documentRecord.vehicle_id || '');

  const heading = document.createElement('strong');
  heading.textContent = 'Документ принят';

  const name = document.createElement('span');
  name.className = 'scan-upload-receipt-name';
  name.textContent = documentRecord.original_name || 'Загруженный документ';

  const status = document.createElement('small');
  status.className = 'scan-upload-receipt-status';
  status.textContent = documentRecord.status === REVIEW_STATUS
    ? 'Нужно проверить распознанные данные'
    : 'Документ добавлен во входящие';

  const actions = document.createElement('div');
  actions.className = 'scan-upload-receipt-actions';

  if (VIEWABLE_MEDIA_TYPES.has(documentRecord.media_type)) {
    actions.append(createAction(
      `/api/documents/${encodeURIComponent(documentRecord.id)}/file`,
      'Открыть оригинал',
      'scan-upload-open',
      true,
    ));
  }

  if (documentRecord.status === REVIEW_STATUS) {
    actions.append(createAction(
      `/documents/${encodeURIComponent(documentRecord.id)}/review`,
      'Проверить данные',
      'scan-upload-review',
    ));
  }

  const inboxButton = document.createElement('button');
  inboxButton.type = 'button';
  inboxButton.className = 'scan-upload-inbox';
  inboxButton.textContent = 'Показать во входящих';
  inboxButton.addEventListener('click', () => {
    document.querySelector('#refreshDocuments')?.click();
    document.querySelector('#documentInbox')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  actions.append(inboxButton);

  panel.append(heading, name, status, actions);
  panel.hidden = false;
  globalThis.dispatchEvent(new CustomEvent('autopassport:document-accepted', {
    detail: { document: documentRecord },
  }));
}

const nativeFetch = globalThis.fetch.bind(globalThis);
globalThis.fetch = async (...args) => {
  const response = await nativeFetch(...args);
  const requestUrl = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
  const method = String(args[1]?.method || 'GET').toUpperCase();

  if (response.ok && method === 'POST' && /\/api\/vehicles\/[^/]+\/documents$/.test(requestUrl)) {
    response.clone().json().then(renderAcceptedDocument).catch(() => {});
  }

  return response;
};

const style = document.createElement('style');
style.textContent = `
  .scan-upload-receipt{margin-top:14px;padding:14px;border:1px solid #b9ddcf;border-radius:18px;background:#f3fbf7;text-align:left}
  .scan-upload-receipt strong,.scan-upload-receipt-name,.scan-upload-receipt small{display:block}
  .scan-upload-receipt strong{font-size:1rem;color:#0f6b5a}
  .scan-upload-receipt-name{margin-top:5px;font-weight:800;overflow-wrap:anywhere}
  .scan-upload-receipt small{margin-top:4px;color:#60716c}
  .scan-upload-receipt-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
  .scan-upload-receipt-actions a,.scan-upload-receipt-actions button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;padding:9px 12px;border-radius:12px;font:inherit;font-weight:800;text-decoration:none;cursor:pointer}
  .scan-upload-review{background:#0f6b5a;color:#fff}
  .scan-upload-open,.scan-upload-inbox{background:#fff;color:#17212b;border:1px solid #d6e4de}
  .scan-upload-receipt-actions :focus-visible{outline:3px solid #f5b544;outline-offset:2px}
`;
document.head.append(style);

setTimeout(ensureReceiptPanel, 0);
