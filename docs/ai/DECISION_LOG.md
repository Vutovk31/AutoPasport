# AutoPassport Decision Log

## ADR-026-001 — Single integrator for `main`

Date: 2026-07-29
Status: accepted

Decision:
- Only the canonical PM/CTO chat integrates changes into `main`.
- Backend work is performed in `agent/backend`.
- MVE/UX work is performed in `agent/mve-ui`.
- Worker chats must provide a handoff with commit SHA, changed files, actual test evidence, risks, and merge instructions.

Reason:
Parallel direct writes to `main` can overwrite files, create conflicting migrations, and invalidate test evidence.

## ADR-026-002 — Red release gate freezes feature merges

Date: 2026-07-29
Status: accepted

Decision:
A failing `autopassport/release-check` blocks new feature merges. Workers may repair assigned regressions in parallel, but the integrator merges only reviewed, minimal, green increments.

Current evidence:
- reviewed main: `7d0252c88581e11c271ffb5285933b786b6080a6`
- release result: 20 failed, 222 passed, 1 warning
- failed step: `test_suite`

## ADR-026-003 — AI output remains an owner-reviewable draft

Date: 2026-07-29
Status: accepted

Decision:
OCR/AI extraction may create or update `DocumentAIDraft` and set a document to `needs_review`. It must not create a `ServiceVisit` or vehicle-history record before explicit owner confirmation.

## ADR-026-004 — No fake parser and no provider commitment yet

Date: 2026-07-29
Status: accepted

Decision:
Production code must not fabricate OCR output. The parser architecture remains provider-neutral until a real provider is selected, its privacy/cost constraints are reviewed, and an explicit integration task is approved.

## ADR-026-005 — Repository naming alias

Date: 2026-07-29
Status: accepted

Decision:
Project instructions may refer to `Vutovk31/AutoPasport`. The GitHub connector resolves that repository to the current canonical repository `Vutovk31/AutoPasport0.1`. All branch and commit operations must verify the resolved repository before writing.