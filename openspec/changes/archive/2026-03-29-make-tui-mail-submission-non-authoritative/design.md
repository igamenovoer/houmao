## Context

Houmao mailbox work currently spans three different execution modes:

- manager-owned direct execution,
- gateway-backed execution,
- TUI-mediated prompt execution through a live LLM session.

Those modes do not provide the same level of truth.

For direct manager execution and gateway-backed execution, Houmao owns the protocol interaction and can safely report mailbox success or failure. For TUI-mediated execution, Houmao only owns request submission into an LLM-driven terminal session. Anything after that point depends on model behavior, tool use, transcript shape, and TUI recovery quality.

Recent live mailbox testing showed the mismatch clearly: a local-interactive Claude session delivered the email and visibly printed a fresh mailbox sentinel block, but the manager command still hung because the TUI observer could not recover one exact active-request result surface from the pane. That is not a transport failure. It is a contract failure: the CLI promised stronger truth than the TUI path can reliably support.

This change therefore treats execution authority as a first-class concept in mailbox command semantics.

## Goals / Non-Goals

**Goals:**
- Distinguish authoritative mailbox outcomes from non-authoritative TUI request submission outcomes.
- Make `houmao-mgr` mailbox commands honest about what they can verify.
- Keep TUI parsing useful for liveness, request submission tracking, and optional preview without making it the mailbox correctness boundary.
- Preserve strong verified results for manager-owned direct and gateway-backed mailbox execution.
- Align the current mailbox refactor direction with a contract that does not depend on exact LLM/TUI reply-schema compliance.

**Non-Goals:**
- Redesign mailbox transports, message schema, or storage layout.
- Remove TUI-mediated mailbox fallback entirely in this change.
- Remove sentinel parsing as a diagnostic or preview aid everywhere.
- Replace protocol-owned verification surfaces such as mailbox check/status with transcript-derived summaries.

## Decisions

### 1. Mailbox command outcomes are classified by execution authority

Mailbox commands will distinguish two classes of completion:

- **verified execution**
  - manager-owned direct execution
  - gateway-backed execution
- **submission-only execution**
  - TUI-mediated prompt submission into a live LLM session

Only verified execution may claim mailbox success or mailbox failure for the requested operation.

TUI-mediated execution may claim only:

- request submitted,
- request rejected before submission,
- session busy,
- interrupted,
- TUI/runtime error.

Alternative considered:

- Keep one result contract for all execution modes.
  Rejected because it forces the weakest execution path to define the trust model for the strongest ones, and it keeps TUI transcript parsing as a false correctness boundary.

### 2. TUI-mediated mailbox commands complete on request lifecycle, not reply-schema recovery

For TUI-mediated manager commands, completion is based on whether Houmao could submit the request turn safely into the live session and maintain basic session-state confidence.

The manager command must not wait for an exact structured mailbox result payload as the condition for returning a command result.

TUI-mediated mailbox result envelopes should therefore look like submission state, not protocol state. The command may include:

- `status`
- `authoritative=false`
- execution mode metadata
- session identity or turn-tracking metadata
- optional preview text or observed markers
- operator verification guidance

Alternative considered:

- Continue waiting for the exact sentinel-delimited schema but treat failures as softer warnings.
  Rejected because it still makes exact TUI parsing the operative completion gate and therefore preserves the same class of hangs and false failures.

### 3. TUI parsing is retained for state tracking and preview only

Shadow parsing and pane recovery remain useful for:

- submit-ready versus busy state,
- provisional post-submit activity,
- interruption detection,
- operator-visible preview,
- debugging evidence.

They are no longer the source of truth for mailbox outcome when the execution path is TUI-mediated.

If Houmao does recover a parseable sentinel block in that mode, it may surface it as optional preview or diagnostic metadata. It must not be required for the command to return.

Alternative considered:

- Remove TUI parsing from mailbox flows entirely.
  Rejected because TUI parsing still provides operational value for readiness, rejection, and debugging even after mailbox truth is decoupled from transcript recovery.

### 4. Verification moves to manager-owned or protocol-owned follow-up surfaces

When the execution mode is non-authoritative, mailbox verification is a separate concern.

The supported verification path must point operators to manager-owned or protocol-owned state, such as:

- `houmao-mgr agents mail status`
- manager-owned mailbox `check` when direct execution is available
- project mailbox inspection for filesystem transports
- transport-native mailbox verification for real email services

This makes verification explicit instead of pretending that one TUI turn can prove protocol outcome reliably.

Alternative considered:

- Auto-run a hidden verification follow-up after every TUI-mediated command.
  Rejected because it reintroduces ambiguity, adds hidden state transitions, and can still fail for reasons unrelated to the original request submission.

### 5. `houmao-mgr` should prefer direct execution and downgrade cleanly when it cannot

This change strengthens the existing mailbox refactor direction:

- prefer manager-owned direct execution,
- fall back to TUI-mediated submission only when necessary,
- downgrade the claimed result semantics when the fallback is used.

That means the same CLI family may return stronger or weaker guarantees depending on execution path, but the contract remains honest because the result envelope carries the authority level explicitly.

Alternative considered:

- Make all mailbox command outcomes submission-only, even for direct execution.
  Rejected because it discards useful verified behavior on code paths where Houmao already owns the protocol interaction.

## Risks / Trade-offs

- `[Two result strengths may confuse users]` -> Mitigate with an explicit `authoritative` field and clear docs that distinguish verified results from submitted requests.
- `[Existing automation may expect parsed mailbox-result JSON from all paths]` -> Mitigate by scoping the semantic downgrade to TUI-mediated manager paths and documenting the new result envelope clearly.
- `[Submission-only `check` may feel weaker than expected]` -> Mitigate by preferring manager-owned direct check execution wherever possible and documenting verification alternatives when fallback occurs.
- `[Preview data may tempt future callers to treat it as authoritative again]` -> Mitigate by treating preview fields as optional diagnostics and keeping authoritative status in a dedicated field.

## Migration Plan

1. Revise the mailbox command specs and docs to define authority-aware outcomes.
2. Introduce the new manager result envelope shape for TUI-mediated fallback.
3. Update local `houmao-mgr agents mail ...` and the planned self-scoped `houmao-mgr mail ...` design to use verified direct execution when available and submission-only fallback otherwise.
4. Keep existing TUI parsing utilities for readiness and preview, but remove them from the command-success boundary.
5. Preserve rollback simplicity by keeping transport execution code unchanged while reverting only the manager contract layer if needed.

## Open Questions

- Should the low-level runtime `python -m houmao.agents.realm_controller mail ...` surface adopt the same non-authoritative TUI semantics, or should this change be limited to `houmao-mgr`?
- Should TUI-mediated submission results include an explicit `turn_id` or similar durable tracking token when available?
- Should there be an explicit operator flag such as `--wait-preview` or `--wait-best-effort` for callers who want more transcript preview without changing the authoritative outcome contract?
