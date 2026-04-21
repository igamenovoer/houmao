## Context

`houmao-mgr` already has a partial operator-facing error model: many command paths convert domain failures into `click.ClickException`, and the top-level wrapper already renders several expected exception types without a traceback. That pattern is not applied consistently across the maintained CLI tree, though, so some ordinary bad-state flows still escape as raw `FileNotFoundError`, `ValueError`, or mailbox-domain exceptions.

The exploration for this change confirmed real leaks in at least four places:

- generic mailbox inspection and maintenance commands operating on unbootstrapped roots,
- project-scoped mailbox inspection paths operating on selected overlays whose mailbox index has not been initialized,
- project recipe inspection paths that parse malformed preset files,
- project role inspection paths that traverse malformed preset references.

The repo already uses helper patterns such as `_load_*_or_click()` in shared command modules, which gives us a clear existing direction: expected domain failures should be normalized close to the command/helper boundary, while the root CLI wrapper should still ensure that no maintained command ever surfaces a Python traceback to the operator.

## Goals / Non-Goals

**Goals:**

- Ensure maintained `houmao-mgr` command failures render as CLI error text rather than Python tracebacks.
- Preserve or improve actionable, scope-aware recovery guidance for expected bad-state flows.
- Reduce command-family drift by moving repeated exception normalization into shared helper boundaries where possible.
- Add regression coverage for representative leaked-exception scenarios and for the root no-traceback safety net.

**Non-Goals:**

- Change successful command payloads, output formats, or supported verbs.
- Redesign mailbox, project, or preset storage models.
- Guarantee polished family-specific wording for every future bug in one step; this change establishes the safety net and fixes confirmed command families first.

## Decisions

### Decision: Use a layered CLI error boundary

Expected operator-facing failures will continue to be normalized near the command or shared-helper boundary, where the code has enough context to render the right message. A final root-level catch-all will serve as a safety net so that uncaught exceptions from maintained command trees still render as CLI error text rather than a traceback.

This is better than a root-only solution because a root-only catch-all cannot reliably choose the correct recovery guidance for scoped commands such as `houmao-mgr project mailbox ...`. It is also better than a command-only audit because future leaks can still happen; the root wrapper must remain operator-safe even when a family misses a local conversion.

### Decision: Normalize exception translation in shared command helpers, not only in leaf commands

Where a command family already routes through shared helpers, the implementation will prefer `_or_click`-style helper entry points or equivalent wrapper functions that convert known domain exceptions into `click.ClickException`. This keeps siblings consistent and reduces the chance that one verb in a family drifts away from the others.

This is especially important for mailbox support helpers and project command helpers that currently sit between leaf commands and lower-level parsers or mailbox-domain operations.

### Decision: Keep project-aware recovery wording at the project command layer

Generic mailbox helpers may still emit generic mailbox-root errors, but project-scoped commands must preserve selected-overlay-aware wording and project-scoped recovery guidance. In practice, that means project mailbox failure paths should recommend `houmao-mgr project mailbox init` when the selected overlay mailbox root lacks required bootstrap state, rather than reusing generic wording that points operators at `houmao-mgr mailbox init`.

This avoids flattening the UX across scopes and preserves the repo's existing selected-overlay wording model.

### Decision: Test both the root wrapper contract and family-specific bad-state flows

Regression coverage will be added at two layers:

- root-wrapper tests that prove uncaught failures do not produce a traceback,
- family-specific command tests that prove known bad-state flows render actionable error text and preserve non-zero exit behavior.

The root-level tests protect the global no-traceback contract. The family-specific tests protect the command wording and the exact recovery guidance for known cases such as uninitialized mailbox indexes and malformed preset files.

## Risks / Trade-offs

- [Risk] A root catch-all can make real programmer bugs look like ordinary command failures. → Mitigation: keep family-specific normalization as the primary UX path, preserve non-zero exit behavior, and use the root catch-all only as a last resort.
- [Risk] Fixing only leaf commands would leave future siblings exposed to the same bug shape. → Mitigation: favor shared helper wrappers and add targeted regression tests around those helper entry points.
- [Risk] Generic mailbox wording could leak into project-scoped flows and recommend the wrong recovery command. → Mitigation: keep project-aware translation at the project command layer and add project-scoped regression tests that assert the recovery guidance.

## Migration Plan

No data migration is required. This is a CLI-behavior and test-only change.

Rollout is the normal code-and-test merge path:

1. update the root wrapper and targeted command/helper paths,
2. add regression tests for known leaked-exception scenarios,
3. run the maintained `srv_ctrl` unit coverage that exercises the CLI wrapper and affected command families.

Rollback is a straightforward code revert if the new root safety-net wording or helper conversions prove too broad.

## Open Questions

None for the proposal-ready design. The implementation can treat the root safety net as a narrow last-resort guard while the targeted family fixes preserve detailed operator guidance.
