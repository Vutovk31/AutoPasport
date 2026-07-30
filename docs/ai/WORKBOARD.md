# AutoPassport AI Workboard

Updated: 2026-07-30
Repository: `Vutovk31/AutoPasport0.1` (currently resolved by GitHub as `Vutovk31/APv1`)
Canonical branch: `main`

## Current main

- Reviewed head: `a2025864568e89dd33559d802a3eee0d77c58fa8`
- Release gate: **BLOCKED**
- Latest factual CI run: `30557835645`
- CI status: `autopassport/release-check` failed
- Latest detailed pytest evidence remains run `30531487181`: `20 failed, 222 passed, 1 warning in 29.64s`

No feature or regression-repair branch may be merged until its assigned tests are factually green and the integrator has reviewed the diff.

## Product boundary

Document upload -> inbox -> AI draft -> owner review -> explicit confirmation -> ServiceVisit -> vehicle passport. AI output remains a draft until owner confirmation.

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

Each worker must classify every assigned failure as a production defect or stale contract assertion.

## Backend assignment

- Task: `APP-026-CI-01C`
- Branch: `agent/backend`
- Status: identical to reviewed `main`; no completed implementation or handoff
- Scope: assigned backend models, parser runner, storage, readiness and tests only

Acceptance criteria:
1. Resolve or correctly reclassify all 14 failures.
2. Preserve owner scoping, review boundary, path traversal and symlink protection.
3. Use a real database readiness probe and report the active storage backend.
4. Record base SHA, commit SHA, changed files, exact test command, result and duration in `docs/ai/BACKEND_HANDOFF.md`.
5. Do not modify MVE-owned files or merge into `main`.

## MVE assignment

- Task: `MVE-026-CI-01C`
- Branch: `agent/mve-ui`
- Status: returned for rework; ahead by 2 commits and behind by 10 commits
- Reviewed commit: `749ed2ce41f396744b953fd433b1b5643a25cf5f`
- Decision: **NOT MERGED**

Blocking findings:
1. The candidate changes only one of three failing MVE test files.
2. No factual pytest or CI evidence exists for the branch.
3. The branch must synchronize with current `main`.
4. `MVE_HANDOFF.md` still reports old task `MVE-026-CI-01` and old base SHA.

Acceptance criteria:
1. Classify and resolve all six MVE failures.
2. Preserve explicit owner confirmation and navigation to exact returned `visit_id`.
3. Prevent repeated confirmation during the request and after success.
4. Use real GET, PATCH and confirm endpoints.
5. Do not introduce a second shell or synthetic parser data.
6. Run `pytest -q tests/test_confirmed_visit_post_flow.py tests/test_document_review_confirmation_frontend.py tests/test_document_review_page.py`.
7. Record exact results and commit in `docs/ai/MVE_HANDOFF.md`.
8. Do not modify backend-owned files or merge into `main`.

## Integration queue

- Backend: waiting for a complete 14-failure handoff with factual test evidence.
- MVE: waiting for synchronization and a complete 6-failure handoff with factual test evidence.
- Main: feature merges frozen.

## Known blockers

1. Current `main` release-check is red; its detailed test matrix was not retrieved in this review.
2. Latest detailed pytest evidence remains `20 failed, 222 passed, 1 warning`.
3. No real OCR/AI provider is approved or configured.
4. Render runtime is not verified.
5. Production parser dispatch remains `disabled`.
6. Mobile runtime at 320-430 px is not verified in a real browser.
7. No new factually green worker increment was submitted.

## Next integration action

Review the first complete worker handoff, verify its base SHA, commit, diff and factual test output, merge only the smallest green repair, then run the full release gate on the resulting `main`.
