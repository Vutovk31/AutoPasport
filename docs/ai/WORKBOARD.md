# AutoPassport AI Workboard

Updated: 2026-07-29
Canonical repository alias: `Vutovk31/AutoPasport` → GitHub repository `Vutovk31/AutoPasport0.1`
Canonical branch: `main`

## Current main

Product-code commit reviewed: `7d0252c88581e11c271ffb5285933b786b6080a6`
Governance baseline before this update: `1eb07755666a5ac2e86d96e97fdef0e3aeafb571`
Release gate: **BLOCKED**
Confirmed CI result: `20 failed, 222 passed, 1 warning`.
Failed release step: `test_suite`.

No feature branch may be merged into `main` until its assigned regression set is green and the integrator has reviewed the diff.

## Product vector

Mobile App Shell
→ Scan document
→ Document Inbox
→ OCR/AI draft parser
→ owner review
→ explicit confirmation
→ ServiceVisit
→ electronic vehicle passport.

## BACKEND

Task: `APP-026-CI-01`
Status: assigned
Branch: `agent/backend`
Objective: restore backend release-gate compatibility after the parser/storage/readiness increments.

Allowed production files:
- `app/models.py`
- `app/document_parser_runner.py`
- `app/document_storage.py`
- `app/document_storage_health.py`
- `app/readiness.py`
- backend-only helper modules required by the failing tests

Allowed tests:
- `tests/test_document_ai_draft_persistence.py`
- `tests/test_document_inbox_persistence.py`
- `tests/test_document_parser_runner.py`
- `tests/test_document_storage_boundary.py`
- `tests/test_document_storage_health.py`
- `tests/test_document_storage_read_boundary.py`
- `tests/test_readiness.py`

Acceptance criteria:
1. Diagnose each assigned failure from the confirmed CI report; do not merely weaken assertions.
2. Preserve owner scoping and the AI review boundary.
3. Preserve storage path traversal and symlink protection.
4. Readiness must execute a real database probe and report storage backend accurately.
5. Run the assigned pytest set and record the exact command and result in `docs/ai/BACKEND_HANDOFF.md`.
6. Do not touch `app/static/**`, `app/document_review_page.py`, or `app/confirmed_visit_page.py`.
7. Do not merge into `main`.

## MVE / UX

### Reviewed result

Prior task: `MVE-DOC-INBOX-001`
Commit presented: `c0b746788bf32ca416a6db5fd6171efc03dd6129`
Decision: **RETURNED FOR REWORK — NOT MERGED**

Reasons:
- the implementation is a detached `app/static/mve/index.html` page with no FastAPI route or integration into the existing Mobile App Shell;
- the branch reports only static contract checks and has no confirmed CI status;
- it duplicates navigation and visual tokens instead of consolidating the existing application shell;
- current `main` already has release-blocking review/confirmation UI regressions that must be repaired first;
- the prototype may be reused as design input, but must not be copied into `main` as a second standalone application.

### Active assignment

Task: `MVE-026-CI-01`
Status: assigned
Branch: `agent/mve-ui`
Objective: restore the owner review/confirmation UI contract without fabricating parser results.

Allowed production files:
- `app/document_review_page.py`
- `app/confirmed_visit_page.py`
- `app/static/**` only where required by the same review/confirmation flow

Allowed tests:
- `tests/test_confirmed_visit_post_flow.py`
- `tests/test_document_review_confirmation_frontend.py`
- `tests/test_document_review_page.py`
- related frontend contract tests only

Acceptance criteria:
1. First synchronize the branch with current `main` while preserving the prior prototype commit for reference.
2. Keep the mobile review screen connected to the real draft GET/PATCH/confirm endpoints.
3. After confirmation, open the exact created visit returned by the API; do not depend on a hash-only redirect.
4. Keep the explicit warning that history is unchanged until owner confirmation.
5. Prevent repeat confirmation while a request is in progress.
6. Do not add mock OCR, fake vehicle data, or synthetic parser results.
7. Run the assigned pytest set and record the exact command and result in `docs/ai/MVE_HANDOFF.md`.
8. Do not touch SQLAlchemy models, migrations, parser runner, storage, or readiness.
9. Do not merge into `main`.

## Integration queue

- Backend: waiting for `APP-026-CI-01` handoff.
- MVE: prior prototype returned; waiting for `MVE-026-CI-01` handoff.
- Main: feature merges frozen until CI regressions are resolved.

## Known blockers

1. Full release check currently fails in the test suite.
2. No real OCR/AI provider adapter has been approved or configured.
3. Render runtime after the latest parser lifespan change has not been verified.
4. Current production parser dispatch default remains `disabled`.

## Integrator next action

Review the first completed CI-repair handoff, compare its branch against `main`, verify actual test evidence, and merge only the smallest green increment.