## Context

The investigation showed that the interactive CAO demo hang is caused by the `shadow_only` readiness gate, not by a failed subprocess launch or a dead CAO session. `run_demo.sh send-turn` delegates to `brain_launch_runtime send-prompt`, and the CAO shadow path waits until the provider parser reports a surface that both looks supported and safely accepts input.

Today the Claude and Codex shadow parsers mark `ui_context="slash_command"` by searching the entire `mode=full` scrollback for slash-command lines. That makes historical `/model` or similar command echoes sticky: even after the tool has returned to a later normal prompt, the parser can keep `accepts_input=false`, the runtime keeps polling for readiness, and demo `send-turn` appears hung until the outer subprocess times out or the operator interrupts it.

This change crosses parser logic, CAO runtime readiness, and the interactive demo contract, so it benefits from explicit design before implementation.

## Goals / Non-Goals

**Goals:**
- Make shadow-parser slash-command classification follow the active input region instead of any slash-command text still visible in historical scrollback.
- Preserve safe blocking while a provider is truly in a slash-command or selection context.
- Allow CAO `shadow_only` prompt submission to resume automatically once the visible surface has returned to a normal prompt.
- Capture the user-facing regression in the interactive CAO demo contract and regression tests.
- Apply the fix consistently across both Claude and Codex shadow parsers where the same history-sensitive heuristic exists.

**Non-Goals:**
- Redesigning the broader CAO turn monitor or changing `cao_only` behavior.
- Introducing a new parser family or a second readiness source for CAO shadow mode.
- Reworking interactive demo UX beyond the blocked `send-turn` behavior.
- Solving the separate `inspect` ambiguity where raw CAO terminal status can still look `idle` while shadow readiness is not yet known to be safe.

## Decisions

### 1. Slash-command context will be derived from the active prompt region, not from whole-scrollback matches

Provider shadow parsers will treat slash-command context as a property of the currently active input surface, not as a sticky property of the full transcript.

In practice, this means parser classification must be based on the newest prompt-region evidence near the live cursor/editable prompt, rather than on any earlier `/...` line still present elsewhere in `mode=full` output. Historical slash-command echoes and completed slash-command results may remain visible in dialog projection, but they must not keep the current surface classified as `slash_command` after the UI has returned to a normal prompt.

Rationale:
- The active readiness question is “would new terminal input go to the normal prompt right now?”, not “did a slash command appear anywhere in this transcript?”
- The current whole-scrollback heuristic creates false negatives for readiness after `/model` and similar flows.
- The same heuristic exists in both Claude and Codex parsers, so the fix should codify a shared expectation.

Alternatives considered:
- Keep the whole-scrollback slash search and add a runtime timeout/escape hatch. Rejected because it preserves the incorrect parser contract and turns a deterministic classification bug into a delayed runtime failure.
- Ignore slash-command context entirely and treat any idle prompt as input-safe. Rejected because that could submit turns into genuinely active command-palette or slash-command states.

### 2. Runtime readiness will continue to trust parser `accepts_input`; the fix belongs in parser classification

The CAO `shadow_only` runtime will keep its current separation of concerns: parsers decide whether the visible surface safely accepts input, and runtime readiness waits for that signal before sending terminal input.

The change therefore focuses on making parser `accepts_input` accurate after slash-command recovery, rather than teaching runtime code to override `slash_command` classifications with special cases.

Rationale:
- `accepts_input` is already the canonical readiness gate used by the runtime.
- A runtime-side exception for “historical slash command” would duplicate parser semantics and likely drift across providers.
- Keeping readiness logic simple makes future UI-format updates easier to reason about and test.

Alternatives considered:
- Add a runtime exception that treats `ui_context="slash_command"` plus `activity="ready_for_input"` as safe. Rejected because truly active slash-command prompts can also present as ready-looking idle surfaces, so a blanket override would be unsafe.
- Teach the demo wrapper to bypass readiness after manual model switches. Rejected because the bug is in the shared runtime/parser path, not in demo-only orchestration.

### 3. The demo contract will describe recovered slash-command/model-switch flows as part of normal multi-turn use

The interactive CAO full-pipeline demo spec will explicitly require that follow-up `send-turn` operations continue to work after an operator performs an in-session slash command or manual model switch, so long as the provider surface has already returned to its normal prompt.

Rationale:
- This is the user-facing failure mode that triggered the investigation.
- The demo should remain a trustworthy reproduction harness for long-lived CAO sessions that operators may manipulate manually between automated turns.
- Capturing the scenario at the demo layer ensures the regression is visible even if lower-level parser behavior changes again later.

Alternatives considered:
- Leave the behavior implicit in runtime specs only. Rejected because the regression was discovered through the demo workflow, and the demo contract should name the operator-visible guarantee directly.

### 4. Regression coverage will distinguish active slash-command surfaces from historical slash-command history

Tests will cover both sides of the distinction:
- an actually active slash-command surface still blocks prompt submission, and
- a recovered normal prompt with historical slash-command lines still visible no longer blocks prompt submission.

Rationale:
- The current failure came from conflating these two cases.
- A single “slash command exists somewhere” fixture is not enough to protect the intended semantics.
- Cross-provider fixtures keep Claude and Codex aligned on the same readiness principle.

## Risks / Trade-offs

- [Risk] Active-prompt inference may still be brittle if Claude or Codex changes how slash-command UI is rendered. -> Mitigation: keep fixtures focused on active-vs-historical prompt semantics and preserve parser diagnostics so future drift is easier to detect.
- [Risk] Relaxing slash-command detection too far could allow prompt submission while a command palette is still active. -> Mitigation: retain explicit blocking for truly active slash-command and selection/approval surfaces, with dedicated regression coverage.
- [Risk] Provider implementations may diverge if only the Claude parser is fixed. -> Mitigation: scope the design and tests across both Claude and Codex where the same full-scrollback heuristic is present.
- [Risk] Operators may still see `inspect` report raw CAO `idle` even when shadow readiness is the stricter concept. -> Mitigation: treat that as out of scope for this change and keep the proposal focused on the blocked `send-turn` regression.

## Migration Plan

1. Update the change specs for `brain-launch-runtime`, `versioned-shadow-parser-stack`, and `cao-interactive-full-pipeline-demo` to capture active-prompt slash-command semantics.
2. Adjust Claude and Codex shadow parser fixtures/tests so active slash-command surfaces remain blocked while historical slash-command lines no longer poison later normal prompts.
3. Validate CAO `shadow_only` runtime tests against both blocked and recovered slash-command surfaces.
4. Add or update interactive demo regression coverage to prove `send-turn` stays usable after manual slash-command/model-switch interaction.
5. Implement the parser/runtime changes and run the affected parser, runtime, and demo test suites.

Rollback is straightforward because the behavior is isolated to parser/readiness semantics and demo expectations. Reverting the parser/rule updates and their regression tests restores the current behavior, though that behavior is known to be incorrect.

## Open Questions

- None blocking. If follow-up work is needed, the most likely adjacent topic is whether `inspect` should eventually expose shadow-readiness state in addition to raw CAO terminal status.
