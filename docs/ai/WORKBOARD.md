# AutoPassport AI Workboard

Updated: 2026-07-30
Repository: `Vutovk31/AutoPasport0.1`
Canonical branch: `main`

## Current main

- Governance head reviewed: `5a72ae6156e3428d99da4378e41a24d7dc575ee4`
- Release gate: **BLOCKED**
- Latest factual CI run: `30523703465`
- CI head SHA: `5a72ae6156e3428d99da4378e41a24d7dc575ee4`
- Confirmed result: `20 failed, 222 passed, 1 warning` in `26.76s`
- Release checks: `7/8` passed; `test_suite` failed

No feature or regression-repair branch may be merged until its assigned test set is factually green and the integrator has reviewed the diff.

## Product vector

Mobile App Shell → Scan document → Document Inbox → OCR/AI draft → owner review → explicit confirmation → ServiceVisit → electronic vehicle passport.

## Failure ownership

### Backend: 14 failures

- `tests/test_document_ai_draft_persistence.py`: 2
- `tests/test_document_inbox_persistence.py`: 2
- `tests/test_document_parser_runner.py`: 1
- `tests/test_document_storage_boundary.py`: 1
- `tests/test_document_storage_health.py`: 3
- `tests/test_document_storage_read_boundary.py`: 1
- `tests/test_readiness.py`: 4

### MVE: 6 failures

- `tests/test_confirmed_visit_post_flow.py`: 1
- `tests/test_document_review_confirmation_frontend.py`: 3
- `tests/test_document_review_page.py`: 2

The current CI run reproduced the same matrix. Each worker must classify every assigned failure as a production defect or stale contract assertion and justify the result.

## Backend assignment

- Task: `APP-026-CI-01C`
- Branch: `agent/backend`
- Status: synchronized with `main`; no implementation submitted
- Scope: models, parser runner, document storage, storage health/read boundary, readiness, and assigned backend tests only

Acceptance criteria:
1. Resolve or correctly reclassify all 14 failures.
2. Preserve owner scoping and the AI review boundary.
3. Preserve path traversal and symlink protection.
4. Use a real database readiness probe and report the active storage backend correctly.
5. Record exact test command, environment, count, duration and commit in `docs/ai/BACKEND_HANDOFF.md`.
6. Do not touch MVE-owned production files or tests.
7. Do not merge into `main`.

## MVE assignment

- Task: `MVE-026-CI-01C`
- Branch: `agent/mve-ui`
- Status: returned for rework; ahead by 2 commits and behind by 4
- Reviewed commit: `749ed2ce41f396744b953fd433b1b5643a25cf5f`
- Decision: **NOT MERGED**

Blocking findings:
1. Six MVE failures remain across three files; the candidate changes only one test file.
2. No factual pytest or CI evidence exists for the branch.
3. The branch must synchronize with current `main` before further work.

Acceptance criteria:
1. Classify and resolve all six MVE failures.
2. Preserve explicit owner confirmation and navigation to the exact returned `visit_id`.
3. Prevent repeated confirmation during the request and after success.
4. Use real GET, PATCH and confirm endpoints.
5. Do not introduce a detached second shell or synthetic parser data.
6. Run `pytest -q tests/test_confirmed_visit_post_flow.py tests/test_document_review_confirmation_frontend.py tests/test_document_review_page.py`.
7. Record exact results and commit in `docs/ai/MVE_HANDOFF.md`.
8. Do not touch backend-owned files or merge into `main`.

## Integration queue

- Backend: waiting for complete 14-failure handoff with factual test evidence.
- MVE: waiting for complete 6-failure handoff with factual test evidence.
- Main: feature merges frozen.

## Known blockers

1. Current full release check has 20 failing tests.
2. No real OCR/AI provider is approved or configured.
3. Render runtime after parser lifespan changes is not verified.
4. Production parser dispatch remains `disabled`.
5. Mobile runtime at 320–430 px is not verified in a real browser.

## Next integration action

Review the first complete worker handoff, verify its commit and factual test output, merge only the smallest green repair, then run the full release gate on the resulting `main`.
