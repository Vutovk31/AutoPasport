# AutoPassport AI Workboard

Updated: 2026-07-30
Canonical repository alias: `Vutovk31/AutoPasport` → GitHub repository `Vutovk31/AutoPasport0.1`
Canonical branch: `main`

## Current main

Product-code commit reviewed: `7d0252c88581e11c271ffb5285933b786b6080a6`
Governance head before this update: `3fc0fc39b79fc99ec759de6fcaac3567bbe3b999`
Release gate: **BLOCKED**
Latest factual CI run: `30520226416` for main SHA `3fc0fc39b79fc99ec759de6fcaac3567bbe3b999`.
Confirmed result: `20 failed, 222 passed, 1 warning` in `29.61s`.
Other release checks: `7/8` passed; only `test_suite` failed.

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

## Latest CI decomposition

The 20 failures are now assigned by non-overlapping ownership:

- **Backend/storage/readiness: 14 failures**
  - `tests/test_document_ai_draft_persistence.py`: 2
  - `tests/test_document_inbox_persistence.py`: 2
  - `tests/test_document_parser_runner.py`: 1
  - `tests/test_document_storage_boundary.py`: 1
  - `tests/test_document_storage_health.py`: 3
  - `tests/test_document_storage_read_boundary.py`: 1
  - `tests/test_readiness.py`: 4
- **MVE review/confirmation: 6 failures**
  - `tests/test_confirmed_visit_post_flow.py`: 1
  - `tests/test_document_review_confirmation_frontend.py`: 3
  - `tests/test_document_review_page.py`: 2

This matrix is the authoritative scope for the next worker increments. Tests must not be weakened merely to match current implementation; each worker must classify every failure as either a production defect or a stale contract assertion and justify the decision in its handoff.

## BACKEND

Task: `APP-026-CI-01C`
Status: assigned; branch is one governance commit behind main and contains no implementation
Branch: `agent/backend`
Objective: resolve the exact 14 backend/storage/readiness failures from CI run `30520226416`.

Allowed production files:
- `app/models.py`
- `app/document_parser_runner.py`
- `app/document_storage.py`
- `app/document_storage_health.py`
- `app/document_storage_read_boundary.py` or the actual read-boundary module if differently named
- `app/readiness.py`
- backend-only helper modules required by the assigned failures

Allowed tests:
- `tests/test_document_ai_draft_persistence.py`
- `tests/test_document_inbox_persistence.py`
- `tests/test_document_parser_runner.py`
- `tests/test_document_storage_boundary.py`
- `tests/test_document_storage_health.py`
- `tests/test_document_storage_read_boundary.py`
- `tests/test_readiness.py`

Acceptance criteria:
1. Rebase or fast-forward `agent/backend` onto current `main` before implementation.
2. Diagnose all 14 assigned failures individually; record production-defect vs stale-test classification.
3. Preserve owner scoping and the AI review boundary.
4. Preserve path traversal and symlink protection; do not reduce security merely to satisfy error-message assertions.
5. Readiness must execute a real database probe and accurately report the selected storage backend.
6. Model and migration assertions must compare schema metadata correctly without relying on SQLAlchemy Column equality semantics.
7. Run the exact assigned pytest set and record command, environment, count and duration in `docs/ai/BACKEND_HANDOFF.md`.
8. If direct execution is unavailable, open a draft PR from `agent/backend` to `main` to obtain GitHub Actions evidence; do not merge it.
9. Do not touch `app/static/**`, `app/document_review_page.py`, `app/confirmed_visit_page.py`, or MVE-owned tests.
10. Do not merge into `main`.

## MVE / UX

### Reviewed result

Task reviewed: `MVE-026-CI-01`
Commit reviewed: `749ed2ce41f396744b953fd433b1b5643a25cf5f`
Decision: **RETURNED FOR COMPLETE FAILURE COVERAGE AND CI EVIDENCE — NOT MERGED**

Positive findings:
- the candidate changes only `tests/test_document_review_page.py` and its handoff;
- source inspection supports the product rule that confirmation uses real endpoints and the exact returned `visit_id`;
- no production code, fake OCR, fake vehicle data or direct AI-to-history write was added.

Blocking findings:
- latest CI has six MVE failures across three test files, but the candidate changes only one of those files;
- `tests/test_confirmed_visit_post_flow.py` still fails on the exact created-visit URL contract;
- `tests/test_document_review_confirmation_frontend.py` still has three failing source-contract assertions;
- the branch has no CI status and no completed pytest command;
- `agent/mve-ui` is diverged from current `main` and is three commits behind.

### Active assignment

Task: `MVE-026-CI-01C`
Status: rework required
Branch: `agent/mve-ui`
Objective: classify and resolve all six MVE review/confirmation failures from CI run `30520226416`, without introducing a second shell or broadening product scope.

Required actions:
1. Synchronize `agent/mve-ui` with current `main`, preserving `749ed2ce41f396744b953fd433b1b5643a25cf5f` as review history.
2. Review all six failures in:
   - `tests/test_confirmed_visit_post_flow.py`
   - `tests/test_document_review_confirmation_frontend.py`
   - `tests/test_document_review_page.py`
3. For each failure, state whether production code or the assertion is wrong, with reference to the canonical product rule.
4. Preserve the explicit owner confirmation boundary and exact `result.visit_id` navigation.
5. Prevent repeated confirmation while a request is active and after success.
6. Use real GET/PATCH/confirm endpoints; do not add mocks or synthetic parser results to production code.
7. Run exactly:
   `pytest -q tests/test_confirmed_visit_post_flow.py tests/test_document_review_confirmation_frontend.py tests/test_document_review_page.py`
8. Record exact pass/fail count, duration, environment, commit SHA and any workflow run in `docs/ai/MVE_HANDOFF.md`.
9. If local execution is unavailable, open a draft PR to obtain factual GitHub Actions evidence; do not merge it.
10. Do not touch models, migrations, parser, storage, readiness or security.

## Integration queue

- Backend: waiting for `APP-026-CI-01C` implementation covering all 14 assigned failures with factual test evidence.
- MVE: prior candidate returned; waiting for `MVE-026-CI-01C` covering all six assigned failures with factual test evidence.
- Main: feature merges frozen until the corresponding regression sets are green.

## Known blockers

1. Full release check fails with 20 tests on current main.
2. No real OCR/AI provider adapter has been approved or configured.
3. Render runtime after the latest parser lifespan change has not been verified.
4. Current production parser dispatch default remains `disabled`.
5. MVE runtime behavior at 320–430 px has not been verified in a real browser.
6. Neither worker branch currently provides factual green CI evidence.

## Integrator next action

Review the first worker handoff that covers its complete assigned failure matrix, verify the referenced commit and CI output, merge only the smallest green regression-repair increment, then run the full release gate on the resulting `main`.