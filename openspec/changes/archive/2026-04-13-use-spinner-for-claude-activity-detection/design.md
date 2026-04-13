## Context

The Claude Code profile currently derives active-turn evidence from a mix of structural terminal signals and fixed prose phrases. The fixed phrase lists include thinking words such as `Musing...` and tool words such as `Reading...`, while `SPINNER_LINE_RE` matches actual spinner-style rows.

That makes readiness brittle. A submit-ready Claude prompt can still be downgraded to `surface.ready_posture=no` when stale or incidental prose matches the phrase lists. The shared session merge then treats that active evidence as stronger than the base ready posture, and gateway prompt-readiness checks correctly reject the surface for the state they receive.

## Goals / Non-Goals

**Goals:**

- Make Claude Code active detection depend on structural current-turn activity evidence rather than fixed thinking/tool phrase vocabulary.
- Preserve active detection when a current spinner/status row or interruptable live-activity surface is visible.
- Preserve latest-turn scoping so old scrollback cannot keep a current prompt-ready surface active.
- Keep the gateway readiness gate unchanged; it should continue to require `turn.phase=ready`, ready surface signals, and stable state.

**Non-Goals:**

- Do not change the public tracked-state response schema.
- Do not change stale-active recovery timing or make recovery a Claude-specific gateway bypass.
- Do not remove Claude prompt-style classification, completion-marker handling, or interrupt/failure classification.
- Do not weaken active detection for non-Claude profiles.

## Decisions

1. Remove Claude active evidence based on fixed thinking/tool prose lists.

   The profile should stop using lists like `THINKING_PATTERNS` and `ACTIVE_TOOL_PATTERNS` as authoritative activity evidence. Those words are product copy, not a stable protocol. Keeping them makes ordinary transcript text and stale scrollback too easy to confuse with current work.

   Alternative considered: expand or tune the phrase lists. Rejected because it preserves the same drift-prone failure mode and will keep chasing Claude text changes.

2. Keep structural active evidence.

   The profile should continue to recognize active UI structure such as spinner-glyph rows, interruptable footer posture, and current active block shape. This keeps the real active path intact while removing dependence on text vocabulary.

   Alternative considered: require only the footer to say it is interruptable. Rejected because the spinner row is the strongest visible work signal and should remain useful when it is clearly current.

3. Treat the spinner as current-state evidence, not scrollback evidence.

   Spinner detection should continue to run only against the latest-turn scoped activity region. If implementation finds that Claude can leave stale spinner rows in that region when the current empty prompt is visibly ready, it should tighten the current-activity region or add a structural guard so a stale spinner line above a ready prompt does not override the ready prompt by itself.

   Alternative considered: ignore all spinner rows whenever an empty prompt is visible. Rejected because Claude can render overlapping current activity near a prompt, and the existing tests preserve that case.

4. Test both sides of the boundary.

   Tests should include a prompt-ready Claude surface with stale or incidental thinking/tool prose and no current spinner evidence; it must remain ready. Tests should also include a current spinner surface and verify it remains active.

## Risks / Trade-offs

- [Risk] Removing prose phrase matching may miss an active Claude surface that lacks both spinner structure and interruptable footer evidence. -> Mitigation: keep structural spinner/footer/block evidence and add a focused active regression test.
- [Risk] The existing latest-turn boundary may still include stale spinner rows if Claude omits a completion marker in a captured transcript. -> Mitigation: add a test that models a ready prompt with stale prose first, then tighten structural spinner scoping if a real stale spinner capture reproduces the same problem.
- [Risk] Changing Claude profile behavior can affect gateway mail-notifier scheduling indirectly. -> Mitigation: leave notifier policy unchanged and verify tracked state rather than bypassing prompt-readiness checks.
