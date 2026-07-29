const STATUS_COPY = {
  uploaded: 'Документ загружен и ожидает обработки',
  processing: 'Распознаём данные документа…',
  needs_review: 'Нужно проверить распознанные данные',
  confirmed: 'Документ подтверждён',
  failed: 'Не удалось обработать документ',
};

const TERMINAL_STATUSES = new Set(['needs_review', 'confirmed', 'failed']);
const POLL_INTERVAL_MS = 3000;
const MAX_ATTEMPTS = 20;
let activeTracker = null;

function updateReceipt(documentRecord) {
  const panel = document.querySelector('#scanUploadReceipt');
  if (!panel || panel.dataset.documentId !== String(documentRecord.id)) return;

  const statusNode = panel.querySelector('.scan-upload-receipt-status');
  if (statusNode) {
    statusNode.textContent = STATUS_COPY[documentRecord.status] || 'Статус документа обновлён';
  }

  let reviewLink = panel.querySelector('.scan-upload-review');
  if (documentRecord.status === 'needs_review' && !reviewLink) {
    reviewLink = document.createElement('a');
    reviewLink.className = 'scan-upload-review';
    reviewLink.href = `/documents/${encodeURIComponent(documentRecord.id)}/review`;
    reviewLink.textContent = 'Проверить данные';
    panel.querySelector('.scan-upload-receipt-actions')?.prepend(reviewLink);
  } else if (documentRecord.status !== 'needs_review') {
    reviewLink?.remove();
  }
}

async function pollDocumentStatus(initialDocument) {
  const vehicleId = initialDocument?.vehicle_id;
  const documentId = initialDocument?.id;
  if (!vehicleId || !documentId) return;

  activeTracker = { documentId: String(documentId), cancelled: false };
  const tracker = activeTracker;
  updateReceipt(initialDocument);

  for (let attempt = 0; attempt < MAX_ATTEMPTS && !tracker.cancelled; attempt += 1) {
    if (TERMINAL_STATUSES.has(initialDocument.status)) return;
    if (attempt > 0) await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS));
    if (tracker.cancelled) return;

    try {
      const response = await fetch(`/api/vehicles/${encodeURIComponent(vehicleId)}/documents`, {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) continue;

      const payload = await response.json();
      const current = Array.isArray(payload?.documents)
        ? payload.documents.find(item => String(item.id) === String(documentId))
        : null;
      if (!current) continue;

      updateReceipt(current);
      initialDocument = current;
      if (TERMINAL_STATUSES.has(current.status)) return;
    } catch (_) {
      // Keep the current UI state and retry within the bounded polling window.
    }
  }
}

globalThis.addEventListener('autopassport:document-accepted', event => {
  if (activeTracker) activeTracker.cancelled = true;
  pollDocumentStatus(event.detail?.document);
});
