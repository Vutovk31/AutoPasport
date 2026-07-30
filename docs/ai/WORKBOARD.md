# AutoPassport AI Workboard

Updated: 2026-07-30
Canonical repository alias: `Vutovk31/AutoPasport` → GitHub repository `Vutovk31/AutoPasport0.1`
Canonical branch: `main`

## Current main

Product-code commit reviewed: `7d0252c88581e11c271ffb5285933b786b6080a6`
Governance head before this update: `1e505d8f0619dcba6d63a5cef0cfd24652308638`
Release gate: **BLOCKED**
Confirmed CI result: `20 failed, 222 passed, 1 warning`.
Failed release step: `test_suite`.

No feature or regression-repair branch may be merged into `main` until its assigned test set is factually green and the integrator has reviewed the diff.

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
Status: assigned; branch synchronized with current governance baseline; no implementation submitted
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

Task: `MVE-026-CI-01`
Commit reviewed: `749ed2ce41f396744b953fd433b1b5643a25cf5f`
Branch base: `204313f6511013eb6d46ce7329ebfea809698cae`
Decision: **RETURNED FOR TEST EVIDENCE — NOT MERGED**

Verified by source inspection:
- the current production page already calls the real draft GET, review PATCH and confirm POST endpoints;
- the page saves draft corrections before confirmation;
- repeated confirmation is blocked with a `confirmed` guard and disabled controls;
- the success link uses the exact `result.visit_id` returned by the confirm API;
- the test-only diff aligns stale assertions with this current production behavior;
- no production code, models, parser, storage, migrations or fabricated data were added.

Reason merge remains blocked:
- no pytest command was executed for the assigned frontend set;
- the commit has no GitHub CI status;
- full `main` release-check remains red.

### Active rework

Task: `MVE-026-CI-01A`
Status: evidence required
Branch: `agent/mve-ui`
Objective: provide factual green test evidence for the existing test-only correction without expanding scope.

Required actions:
1. Run exactly:
   `pytest -q tests/test_confirmed_visit_post_flow.py tests/test_document_review_confirmation_frontend.py tests/test_document_review_page.py`
2. Record the full command, pass/fail count and environment in `docs/ai/MVE_HANDOFF.md`.
3. If a test fails, fix only the smallest contradiction within the assigned review/confirmation scope.
4. Do not add another shell, new routes, fake OCR, fake vehicles or synthetic draft data.
5. Do not touch backend models, migrations, parser, storage, readiness or security.
6. Do not merge into `main`.

## Integration queue

- Backend: branch synchronized; waiting for `APP-026-CI-01` implementation and test evidence.
- MVE: commit structurally accepted, merge blocked pending `MVE-026-CI-01A` test evidence.
- Main: feature merges frozen until CI regressions are resolved.

## Known blockers

1. Full release check currently fails in the test suite.
2. No real OCR/AI provider adapter has been approved or configured.
3. Render runtime after the latest parser lifespan change has not been verified.
4. Current production parser dispatch default remains `disabled`.
5. MVE runtime behavior at 320–430 px has not been verified in a real browser.

## Integrator next action

Review the first worker handoff containing factual test execution, compare its branch against `main`, and merge only the smallest green regression-repair increment.
