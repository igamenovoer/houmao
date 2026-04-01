## Context

`make-operations-project-aware` already moved maintained command families onto one overlay-local root contract, and the follow-up wording and demo cleanup slices are complete. The remaining gap is verification breadth: the current focused tests prove the main refactors compile and the primary paths work, but they do not yet cover the full scenario matrix called out in parent tasks `5.2` and `5.3`.

This follow-up is intentionally verification-oriented. It should strengthen automated coverage across the maintained command families and run representative maintained workflows that now depend on overlay-local defaults, without reopening the underlying root-selection design.

## Goals / Non-Goals

**Goals:**
- Add automated coverage for the project-aware contract across overlay selection, `.git` worktree boundaries, non-creating resolution, implicit bootstrap reporting, overlay-local placement, cleanup override behavior, and server-start behavior.
- Reuse maintained demos and existing fixtures to validate representative operator workflows with fewer explicit root overrides.
- Produce clear validation evidence so `make-operations-project-aware` can be marked apply-ready and archived once the runs pass.

**Non-Goals:**
- Redesign the project-aware root contract or expand maintained command scope beyond the already accepted surfaces.
- Add broad new demo packs or preserve deprecated compatibility entrypoints.
- Require heavyweight end-to-end environments when a targeted unattended or shell-level validation can cover the maintained workflow.

## Decisions

### Decision: Treat this as a verification slice, not another behavior slice

The follow-up will prefer test additions, fixture refinement, and validation harness updates. Production code changes are allowed only when required to make existing maintained behavior observable or testable.

Alternative considered:
- Reopen the parent runtime or CLI specs directly. Rejected because the remaining work is proving the accepted contract, not redefining it.

### Decision: Split coverage into automated matrix verification and representative workflow validation

Automated coverage will target scenario classes that are deterministic in `pytest`, including precedence, nested repository boundaries, payload wording, root placement, cleanup selection, and server config selection. Separate workflow validation will exercise maintained demos or operator flows that prove the contract works in realistic usage with overlay-local defaults.

Alternative considered:
- Rely only on broader demo runs. Rejected because that would leave selection-precedence and nested-boundary edge cases under-specified and hard to localize when broken.

### Decision: Reuse maintained demo surfaces and existing fixtures as the workflow proof points

Representative validation will use maintained assets already aligned with the contract, especially `minimal-agent-launch` and `single-agent-mail-wakeup`, plus focused command-family checks where a demo is not the right surface. Deprecated entrypoints and legacy demo packs remain out of scope.

Alternative considered:
- Add a new dedicated validation demo pack. Rejected because it would add new maintenance surface area just to test a contract that existing maintained workflows already exercise.

### Decision: Record validation evidence in repeatable commands and OpenSpec status, not ad hoc notes

The implementation should end with a short, rerunnable command set: focused `pytest` coverage, any needed demo or shell validations, and `openspec status` or `openspec instructions apply` for the parent change. This keeps the archive decision tied to reproducible evidence.

Alternative considered:
- Depend on informal manual inspection. Rejected because it does not provide a stable close-out contract for the parent change.

## Risks / Trade-offs

- [Risk] Wider validation could drift into broad integration work and slow the close-out. → Mitigation: keep the matrix scoped to maintained project-aware surfaces and use unattended or shell-level workflows where possible.
- [Risk] Representative demo validation can become flaky if it depends on external services or interactive terminals. → Mitigation: prefer maintained demos that already run headlessly or with local isolated fixtures, and keep the pass criteria explicit.
- [Risk] Test-only follow-ups can hide small production issues discovered during validation. → Mitigation: allow narrowly scoped production fixes when required, but keep them directly tied to failing verification scenarios.
