## Context

The project-aware roots change moved maintained launch, mailbox, cleanup, and server flows onto one overlay-local default contract. Most implementation surfaces now resolve the right roots, but operator-facing strings still come from older assumptions in several places:

- generic and project-scoped mailbox help still leads with shared-root language,
- project and project-easy failures still say "discovered project overlay" even when the selected overlay came from an explicit env override or when the command intentionally stayed non-creating,
- server and cleanup runtime-root help still reads like a shared-root-first surface,
- some success and JSON-facing payloads expose bootstrap booleans or resolved roots without consistently explaining what was selected or whether Houmao created it implicitly.

This follow-up is a wording and payload-normalization pass, not another filesystem-contract change.

## Goals / Non-Goals

**Goals:**
- Define one consistent operator vocabulary for selected overlays, overlay-local defaults, shared-root overrides, and implicit bootstrap.
- Apply that vocabulary across maintained project, project easy, mailbox, cleanup, launch, and server command families.
- Keep machine-readable payload changes minimal and deliberate so automation can detect implicit bootstrap or selected-root outcomes without re-learning unrelated schema.

**Non-Goals:**
- Changing root-resolution precedence or any project-aware filesystem behavior.
- Reworking archived or legacy compatibility entrypoints, historical docs, or demo packs outside the maintained command surface.
- Introducing one new universal output schema for every CLI family.

## Decisions

### Decision: Standardize on a small operator vocabulary matrix

Maintained surfaces will use these terms consistently:

- `selected overlay root`: the overlay root resolved for the current invocation, whether from explicit selection, env selection, nearest-ancestor discovery, or implicit bootstrap.
- `active project runtime root` / `active project mailbox root`: overlay-derived defaults used when no stronger explicit or env override wins.
- `shared runtime root` / `shared mailbox root`: only the explicit global env-root or explicit CLI-root path, or the non-project fallback when no project-aware root applies.
- `implicit bootstrap`: a command-created overlay for the current invocation.
- `non-creating resolution`: inspection, removal, stop, and similar flows that intentionally refuse to create the selected or would-bootstrap overlay.

Alternative considered: patch individual help strings and errors in place without a vocabulary contract. Rejected because the repo already drifted that way once.

### Decision: Prefer shared formatter helpers where wording is already centralized

Where commands already share helpers for option help or payload rendering, this change will update or extend those helpers rather than duplicating text in each command:

- runtime-root option help,
- mailbox-root option help,
- project non-creating failure builders,
- payload detail or summary helpers that already emit project-aware bootstrap information.

Alternative considered: touch every `click.option(... help=...)` and `ClickException(...)` inline. Rejected because that makes future wording regressions harder to prevent.

### Decision: Keep JSON payload changes additive and localized

This change will not introduce one cross-surface payload schema. Instead:

- existing stable keys stay in place where possible,
- project-aware payloads that already expose selection or bootstrap state will get clearer wording around those fields,
- new fields are only added when a maintained payload currently cannot express selected-root or implicit-bootstrap information that the user-facing contract now requires.

Alternative considered: unify all project-aware command families under one new root-resolution payload object. Rejected as unnecessary scope for a wording follow-up.

### Decision: Separate ownership-mismatch errors from non-creating-resolution errors

Project and project-easy commands will distinguish:

- no active overlay resolved for this invocation and the command did not create one, versus
- an addressed artifact or managed agent exists but does not belong to the selected overlay.

The first class will describe the selected or would-bootstrap overlay and the fact that the command remained non-creating. The second class will say `selected project overlay` rather than `discovered project overlay`.

Alternative considered: keep the current generic "discovered project overlay" phrasing everywhere. Rejected because it is inaccurate for env-selected overlays and for commands that intentionally resolve without discovery side effects.

## Risks / Trade-offs

- [Risk] Wording-only edits may accidentally break automation that string-matches human output. → Mitigation: preserve machine-readable keys where possible and keep wording changes explicit in focused tests.
- [Risk] Shared helpers may not cover every maintained surface cleanly. → Mitigation: centralize only where code already shares a seam, and document any intentional one-off wording in the touched specs.
- [Risk] Some reference docs may still mention older wording after CLI help is fixed. → Mitigation: keep this change scoped to maintained help, errors, and payloads; any remaining doc sweep can be handled separately.

## Migration Plan

1. Update shared help or output helpers first so generic mailbox, cleanup, and server surfaces inherit the new terminology.
2. Update project and project-easy non-creating or ownership-mismatch errors plus any corresponding JSON detail fields.
3. Update launch and build payload wording where implicit bootstrap or overlay-local root selection needs to be surfaced.
4. Refresh focused tests that assert help text, failure text, or machine-readable payload details.

No filesystem or persisted-data migration is required. Rollback is code-only.

## Open Questions

None at proposal time. The intended scope and vocabulary are specific enough to implement directly.
