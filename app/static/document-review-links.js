const REVIEW_STATUS = 'needs_review';
const REVIEW_LABEL = 'Проверить данные';
let latestDocuments = [];

const nativeFetch = globalThis.fetch.bind(globalThis);
globalThis.fetch = async (...args) => {
  const response = await nativeFetch(...args);
  const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
  if (response.ok && /\/api\/vehicles\/[^/]+\/documents(?:\?.*)?$/.test(url)) {
    response.clone().json().then(payload => {
      latestDocuments = Array.isArray(payload?.documents) ? payload.documents : [];
      queueMicrotask(addReviewLinks);
    }).catch(() => {});
  }
  return response;
};

function addReviewLinks() {
  document.querySelectorAll('.document-inbox-item').forEach((card, index) => {
    const inboxItem = latestDocuments[index];
    const existing = card.querySelector('.document-review-link');
    if (!inboxItem || inboxItem.status !== REVIEW_STATUS || !inboxItem.id) {
      existing?.remove();
      return;
    }
    if (existing) return;

    const link = document.createElement('a');
    link.className = 'document-review-link';
    link.href = `/documents/${encodeURIComponent(inboxItem.id)}/review`;
    link.textContent = REVIEW_LABEL;
    link.setAttribute('aria-label', `${REVIEW_LABEL}: ${inboxItem.original_name || 'документ'}`);
    card.querySelector('div:last-child')?.append(link);
  });
}

const observer = new MutationObserver(addReviewLinks);
observer.observe(document.documentElement, { childList: true, subtree: true });

const style = document.createElement('style');
style.textContent = `
  .document-review-link{display:inline-flex;margin-top:10px;padding:9px 12px;border-radius:12px;background:#0f6b5a;color:#fff;text-decoration:none;font-weight:800;font-size:.86rem}
  .document-review-link:focus-visible{outline:3px solid #f5b544;outline-offset:2px}
`;
document.head.append(style);
