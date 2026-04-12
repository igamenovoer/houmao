## Context

The upstream bug report shows Claude Code returning to a visible empty prompt while gateway mail notification remains deferred because the shared TUI tracker still publishes an active turn. The problematic snapshot shape includes older Claude `Thinking...` and progress rows in tmux scrollback, followed much later by a current `Worked for ...` completion marker and an empty submit-ready prompt.

The mail notifier is behaving correctly for the state it receives: it waits while `turn.phase` is not `ready` or `surface.ready_posture` is not `yes`. The defect is upstream of notification policy. The Claude Code detector is interpreting historical scrollback rows as current activity evidence, which lets stale `thinking_line` evidence downgrade a prompt-ready surface back to active.

## Goals / Non-Goals

Goals:

- Scope Claude Code activity evidence to the current latest-turn region when the current prompt anchor is visible.
- Prevent old Claude thinking, spinner, and tool-progress rows from keeping `turn.phase=active` after the surface has returned to a submit-ready prompt.
- Preserve active-state detection for current live Claude activity, including current spinner/progress rows, interruptable footers, active tool surfaces, slash-command overlays, and real draft editing.
- Add regression coverage using the upstream full-scrollback capture shape.
- Keep gateway mail-notifier readiness gating unchanged.

Non-Goals:

- Do not add a gateway notifier bypass or alternate notification policy for Claude.
- Do not rewrite the shared tracker state machine or introduce a parser dependency for this detector fix.
- Do not change the public tracked-state schema.
- Do not add compatibility shims for older detector behavior.

## Decisions

1. The Claude Code profile will scope activity-like terminal evidence to the current latest-turn region.

   The detector already has a concept of current prompt anchoring for stale status interpretation. Reusing that boundary for activity rows gives the profile enough local context to ignore transcript history without teaching the shared tracker engine about Claude-specific scrollback structure. If no current prompt anchor is visible, the profile should remain conservative instead of asserting ready from incomplete evidence.

2. Historical activity rows will be excluded before normalized active evidence is returned.

   The profile should not emit `thinking_line`, spinner, or equivalent active reasons from rows above the current latest-turn boundary. This keeps `_merge_temporal_hints` from receiving stale active evidence that can override otherwise valid ready posture.

3. Current live activity evidence remains authoritative.

   Rows inside the current latest-turn region, current interruptable footer text, and current modal or slash overlays should continue to affect active or unknown posture. The fix should avoid a blanket "ignore thinking text when a prompt exists" rule because Claude can render active surfaces near the current prompt during an in-flight turn.

4. Tests should model the upstream failure with full scrollback and a smaller tail comparison.

   A regression fixture or synthetic snapshot should include historical thinking/progress rows, a later completion marker, and a final empty prompt. The detector should classify the full snapshot the same way as the current-tail-only snapshot for readiness.

## Risks / Trade-offs

- If the latest-turn boundary is too narrow, a live activity indicator rendered above the final prompt area could be ignored. Tests should include a current active case with visible current activity evidence.
- If the prompt anchor is missing from a capture, the profile may degrade to unknown instead of ready. That is acceptable for safety because the bug report has a visible current prompt anchor.
- This fixes the state source rather than the notifier symptom. Other consumers of shared tracked state get the same corrected readiness semantics, but the implementation must be careful not to weaken active-turn inference for non-Claude profiles.
