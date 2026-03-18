## Context

`shadow_only` CAO turns currently use a generic runtime completion gate: after submit, the runtime waits for the surface to become submit-ready again and requires either projected-dialog drift or a prior `business_state = working` observation as evidence that the turn actually progressed. That generic rule is correct for "the terminal is no longer visibly busy," but it is weaker than the mailbox runtime contract.

Runtime-owned mailbox commands already define a stronger correctness boundary: the command is not complete until exactly one JSON payload for that request is present between `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END`. Live reproduction showed the gap between those layers. Claude returned to a prompt-looking surface before the sentinel payload became visible, so the runtime declared the turn complete and parsed too early even though the agent was still working in tmux and later emitted the correct sentinel block.

The existing parser model is still correct. `business_state` answers whether the TUI appears idle, working, blocked, or unknown. `input_mode` answers whether the current surface accepts freeform input, is modal, or is closed. Those axes are snapshot hints for lifecycle control, not a proof that a command-specific output contract has been satisfied.

## Goals / Non-Goals

**Goals:**

- Preserve the two-axis parser model and the current meaning of `business_state` and `input_mode`.
- Make `shadow_only` mailbox commands wait for their explicit sentinel-delimited result contract instead of treating the first submit-ready rebound as final completion.
- Reuse existing timeout, stall, blocked-surface, unsupported-surface, and disconnect handling instead of inventing a separate mailbox lifecycle.
- Add regression coverage for the delayed-sentinel case that was reproduced against a live Claude sender session.

**Non-Goals:**

- Redesign parser surface assessment or add mailbox-specific parser states.
- Change generic non-mail prompt-turn completion behavior unless that behavior is needed to support command-owned terminal evidence.
- Add hidden retries, fallback prompts, or alternate mailbox result formats.
- Promise exact transcript recovery from shadow dialog projection.

## Decisions

### 1. Keep generic shadow lifecycle completion separate from command-owned completion contracts

The runtime will keep the current generic `shadow_only` lifecycle gate based on `availability`, `business_state`, `input_mode`, and post-submit progress evidence. Mailbox commands will layer a command-owned completion check above that gate.

Rationale:

- The parser states describe "what the surface looks like now," which is the right abstraction for readiness, blocked-state handling, and stall detection.
- The mailbox sentinel contract is semantic command completion, not parser state.
- Reusing the parser axes avoids provider-specific mailbox logic in the parser stack.

Alternatives considered:

- Tighten the generic turn monitor for all turns so submit-ready rebound is never enough. Rejected because generic prompts do not have a universal stronger end marker.
- Add a mailbox-specific parser state. Rejected because sentinel visibility is command-owned output validation, not a provider surface classification.

### 2. Treat generic `shadow_only` completion as provisional for sentinel-driven mailbox commands

For runtime-owned mailbox commands, the first generic completion event becomes a provisional milestone: the terminal appears safe to inspect, but the command is not complete until the sentinel-delimited mailbox result for that request is visible in post-submit shadow text.

Rationale:

- This matches the user-facing mental model: wait until the terminal stops changing, then inspect the text for the explicit mailbox end marker.
- It keeps the existing readiness and stall behavior intact while preventing premature parse failure when the prompt reappears before the mailbox result text is rendered.

Alternatives considered:

- Parse once immediately when the generic turn monitor completes. Rejected because that is the reproduced failure mode.
- Ignore generic completion entirely and scan continuously from submit until sentinel appears. Rejected because the generic lifecycle still provides useful bounded-progress and blocked-surface behavior.

### 3. Poll post-submit shadow text surfaces for mailbox sentinel evidence

Mailbox completion will inspect the available post-submit shadow text surfaces derived from `output?mode=full` and keep polling until one complete mailbox result payload for the active request is observed, or until the existing terminal failure policy fires.

Rationale:

- The sentinel contract is the machine-critical boundary for mailbox commands.
- Shadow dialog projection remains best effort, so the runtime must inspect the text surfaces available after submit rather than assume the first projected dialog snapshot is final.
- Limiting the search to post-submit evidence avoids conflating the current request with older mailbox output still visible in history.

Alternatives considered:

- Require the projected dialog alone to contain the final mailbox result. Rejected because the existing specs already say mailbox correctness must not depend on exact projection fidelity.
- Search arbitrary full scrollback without post-submit scoping. Rejected because historical sentinel blocks from older mailbox requests could create false positives.

### 4. Keep failure semantics bounded and explicit

The mailbox-specific wait path will continue to use the existing turn timeout, stall policy, blocked-surface detection, and unsupported/disconnected surface handling. The change only removes premature "missing sentinel" failure after provisional completion. It does not add automatic retry prompts.

Rationale:

- The live bug is a false early failure, not a need for a longer or hidden retry workflow.
- Reusing the existing bounded lifecycle preserves operator expectations and keeps diagnostics consistent across command types.

Alternatives considered:

- Introduce a separate mailbox timeout or implicit retry prompt. Rejected because it would mask the real lifecycle state and complicate debugging.

## Risks / Trade-offs

- [Mailbox commands may take longer to return when the prompt reappears before the sentinel block] -> Reuse existing timeout and stall bounds so the wait is explicit and limited.
- [A required sentinel may only be visible in a subset of shadow text surfaces] -> Inspect post-submit shadow text surfaces in a deterministic order and keep the mailbox contract anchored to explicit sentinel evidence rather than one projection field.
- [Historical sentinel output from earlier mailbox turns could be mistaken for the active request] -> Scope detection to post-submit observations for the current runtime-owned request.
- [Implementation could accidentally change generic prompt-turn behavior] -> Keep the generic turn monitor contract unchanged and add regression tests that cover both mailbox-specific and non-mail `shadow_only` flows.

## Migration Plan

No data migration is required.

Implementation rollout:

1. Add mailbox-aware completion gating in the runtime prompt/mailbox path while preserving the existing generic turn monitor.
2. Add regression coverage for delayed sentinel arrival after transient submit-ready rebound.
3. Verify existing non-mail `shadow_only` behavior still follows the generic completion contract.

Rollback strategy:

- Revert the mailbox-specific completion layer while leaving the parser and generic turn monitor unchanged.

## Open Questions

- None that block the proposal. Operator-facing diagnostics for "provisional completion waiting on sentinel" can be refined during implementation if needed.
