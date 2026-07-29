import './scan-review.js';
import './scan-upload-receipt.js';

const REVIEW_STATUS = 'needs_review';
const REVIEW_LABEL = 'Проверить данные';
const OPEN_LABEL = 'Открыть документ';
const VIEWABLE_MEDIA_TYPES = new Set(['application/pdf', 'image/jpeg', 'image/png']);
let latestDocuments = [];

const nativeFetch = globalThis.fetch.bind(globalThis);
globalThis.fetch = async (...args) => {
  const response = await nativeFetch(...args);
  const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
  if (response.ok && /\/api\/vehicles\/[^/]+\/documents(?:\?.*)?$/.test(url)) {
    response.clone().json().then(payload => {
      latestDocuments = Array.isArray(payload?.documents) ? payload.documents : [];
      queueMicrotask(addDocumentLinks);
    }).catch(() => {});
  }
  return response;
};

function ensureActionContainer(card) {
  let container = card.querySelector('.document-inbox-actions');
  if (container) return container;

  container = document.createElement('div');
  container.className = 'document-inbox-actions';
  card.querySelector('div:last-child')?.append(container);
  return container;
}

function addDocumentLinks() {
  document.querySelectorAll('.document-inbox-item').forEach((card, index) => {
    const inboxItem = latestDocuments[index];
    const existingReview = card.querySelector('.document-review-link');
    const existingOpen = card.querySelector('.document-open-link');

    if (!inboxItem?.id) {
      existingReview?.remove();
      existingOpen?.remove();
      return;
    }

    const actions = ensureActionContainer(card);
    const canOpen = VIEWABLE_MEDIA_TYPES.has(inboxItem.media_type);
    if (!canOpen) {
      existingOpen?.remove();
    } else if (!existingOpen) {
      const openLink = document.createElement('a');
      openLink.className = 'document-open-link';
      openLink.href = `/api/documents/${encodeURIComponent(inboxItem.id)}/file`;
      openLink.textContent = OPEN_LABEL;
      openLink.target = '_blank';
      openLink.rel = 'noopener';
      openLink.setAttribute('aria-label', `${OPEN_LABEL}: ${inboxItem.original_name || 'документ'}`);
      actions.append(openLink);
    }

    if (inboxItem.status !== REVIEW_STATUS) {
      existingReview?.remove();
      return;
    }
    if (existingReview) return;

    const reviewLink = document.createElement('a');
    reviewLink.className = 'document-review-link';
    reviewLink.href = `/documents/${encodeURIComponent(inboxItem.id)}/review`;
    reviewLink.textContent = REVIEW_LABEL;
    reviewLink.setAttribute('aria-label', `${REVIEW_LABEL}: ${inboxItem.original_name || 'документ'}`);
    actions.append(reviewLink);
  });
}

const observer = new MutationObserver(addDocumentLinks);
observer.observe(document.documentElement, { childList: true, subtree: true });

const style = document.createElement('style');
style.textContent = `
  .document-inbox-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
  .document-review-link,.document-open-link{display:inline-flex;padding:9px 12px;border-radius:12px;text-decoration:none;font-weight:800;font-size:.86rem}
  .document-review-link{background:#0f6b5a;color:#fff}
  .document-open-link{background:#eef2f5;color:#17212b;border:1px solid #d9e0e6}
  .document-review-link:focus-visible,.document-open-link:focus-visible{outline:3px solid #f5b544;outline-offset:2px}
`;
document.head.append(style);
