const REVIEW_STATUS = 'needs_review';
const REVIEW_LABEL = 'Проверить данные';

function escapeSelectorValue(value) {
  return String(value ?? '').replaceAll('\\', '\\\\').replaceAll('"', '\\"');
}

function addReviewLinks() {
  const cards = document.querySelectorAll('.document-inbox-item');
  cards.forEach((card, index) => {
    const document = globalThis.__autoPassportInboxDocuments?.[index];
    if (!document || document.status !== REVIEW_STATUS || !document.id) return;
    if (card.querySelector('.document-review-link')) return;

    const link = document.createElement('a');
    link.className = 'document-review-link';
    link.href = `/documents/${encodeURIComponent(document.id)}/review`;
    link.textContent = REVIEW_LABEL;
    link.setAttribute('aria-label', `${REVIEW_LABEL}: ${document.original_name || 'документ'}`);
    card.querySelector('div:last-child')?.append(link);
  });
}

function exposeInboxDocuments() {
  const source = globalThis.inboxDocuments;
  if (Array.isArray(source)) globalThis.__autoPassportInboxDocuments = source;
}

const observer = new MutationObserver(() => {
  exposeInboxDocuments();
  addReviewLinks();
});

observer.observe(document.documentElement, { childList: true, subtree: true });

const style = document.createElement('style');
style.textContent = `
  .document-review-link{display:inline-flex;margin-top:10px;padding:9px 12px;border-radius:12px;background:#0f6b5a;color:#fff;text-decoration:none;font-weight:800;font-size:.86rem}
  .document-review-link:focus-visible{outline:3px solid #f5b544;outline-offset:2px}
`;
document.head.append(style);

addReviewLinks();
