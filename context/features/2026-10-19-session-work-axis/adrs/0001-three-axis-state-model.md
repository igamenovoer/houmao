# Three-Axis State Model for Managed-Agent Tracking

Status: accepted

Providers with background work broke an implicit conflation in Houmao's tracked state: `prompt-ready == turn-terminal == task-terminal` used to be one observation, and consumers built on it. Claude Code at the supported floor lets an agent end its turn while provider-acknowledged work keeps running, so the composer is ready while the task is not done. State tracking must model these as separate facts instead of letting `ready` imply "done".

## Decision

Tracked state is decomposed into three orthogonal axes:

- `surface.*` (TUI-owned): whether typed input would land, editing posture, pending input, modal rendering, stability. Unchanged.
- `turn.phase` (hook plus TUI): whether a response cycle is in flight. Extended by the hook channel exploration with `blocked`, a hook-only-reachable value meaning "the provider is asking the operator for an action and will not proceed until it is settled".
- `work` (hook-primary, session-scoped): whether provider-acknowledged work is outstanding beyond the current turn: `pending | clear | unknown`.

`settled = (turn.phase == ready) AND (work == clear)` is derived state that recovers the old "assign the next task" meaning without pretending the provider said it.

## Considered Options

- Stretch `turn.phase` to stay non-ready while background work runs. Rejected: it contradicts the accepted decision that hook terminal events flip `phase=ready` immediately, misreports promptability, and the provider genuinely finished the turn.
- Keep `background_work_pending` as an informational payload-mirror flag only. Rejected: without live clearing evidence the flag can say `pending` indefinitely, which fails the capability the axis exists for.
- Let consumers infer background state from raw payloads. Rejected: it pushes provider-specific payload knowledge into every consumer and guarantees inconsistent interpretations.

## Consequences

- The axis needs clearing evidence. The hook channel adopts conditional promotion: spike evidence decides which provider events report background work completion at the floor; if none exist, the axis mirrors the most recent terminal payload and documents the staleness window.
- Admission defaults do not read `work` in this release; `settled` is available for orchestrators and a possible future policy.
- TUI-only and degraded sessions report `work=unknown`, preserving the byte-equivalence gate for existing state.
- Every consumer that assumes prompt-ready means done is inventoried and either adjusted or explicitly recorded as intentionally unchanged.
- `work` interacts freely with other axes: `blocked`, `interrupted`, and maintenance states may all coexist with `work=pending`.

## Related Decisions from the Same Exploration

These were settled alongside the axis and are recorded here for one durable ledger:

- Hook terminal events latch the turn; later TUI settlement for that turn is suppressed, except TUI temporal interrupt evidence may still flip the result to `interrupted`.
- Hook terminal events set `turn.phase=ready` immediately; the repaint window remains visible through TUI surface fields and the `hook_terminal_tui_active` conflict note.
- TUI modal-dismissal evidence (including the positive `User rejected` dialog line) clears a hook-set `blocked` phase back to `active`; the TUI never enters `blocked`.
- The hook posture holds one armed prompt; an overlapping `UserPromptSubmit` supersedes with an orphan diagnostic, and the superseded turn falls back to TUI settlement.
- On recovery from staleness, a late hook terminal event that agrees with a TUI-settled result is a no-op; on disagreement the hook result wins with an explicit correction transition and a `hook_correction_after_staleness` conflict note.
- Startup grace and staleness thresholds ship as fixed 15 s / 30 s defaults, calibrated by live qualification evidence.
- Session cleanup deletes the raw hook event store; revisit if a live failure proves undiagnosable without it.
