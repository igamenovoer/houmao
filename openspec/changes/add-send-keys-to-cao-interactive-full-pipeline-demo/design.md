## Context

The interactive CAO full-pipeline demo already has a stable stateful lifecycle: `start` provisions a run root and launches a long-lived session, `send-turn` records prompt/response artifacts, `inspect` exposes tmux and log affordances, `verify` summarizes prompt turns, and `stop` tears the session down. That shape is useful because operators can keep one session alive while they interact with it manually across multiple commands.

The missing piece is raw control input. The runtime now exposes `send-keys` for CAO-backed tmux sessions, but the demo pack still teaches only prompt-turn submission. Operators who need to drive slash-command menus, move through provider choices, dismiss overlays, or type partial text without auto-submitting must currently leave the tutorial surface and invent their own commands.

This change needs to extend the demo pack without collapsing the distinction between prompt turns and state-shaping control input. The existing `verify` contract, recorded `turns/` artifacts, and wrapper-oriented README all assume that a turn means "prompt submitted, response captured." Raw control-key streams do not fit that model and should stay separate.

## Goals / Non-Goals

**Goals:**
- Add a first-class `send-keys` demo command that reuses the persisted active session identity.
- Reuse the runtime-owned control-input grammar instead of introducing demo-specific key parsing.
- Persist control-input artifacts in a dedicated family so operators and tests can inspect what was sent.
- Keep prompt-turn verification semantics unchanged even when control-input actions happen between turns.
- Extend the README and wrapper workflow so manual control input is part of the documented happy path.

**Non-Goals:**
- Changing the runtime `send-keys` grammar, supported key names, or tmux target-resolution behavior.
- Overloading `send-turn` with flags that make it serve both prompt-turn and raw-input semantics.
- Refactoring the demo into a unified event timeline that merges prompts, control input, inspect output, and verify state.
- Making `send-keys` wait for provider output or interpret UI changes after injection.
- Redefining `verify` to include control-input actions or snapshots.

## Intended Usage Examples

The intended operator workflow keeps prompt turns and raw control input separate:

```bash
# Launch or replace the long-lived tutorial session.
scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh

# Send a normal prompt turn and expect a captured response artifact.
scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh \
  --prompt "Summarize the current workspace state."

# Send a raw control key without creating a prompt turn.
scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh '<[Escape]>'

# Drive a slash-command menu through the runtime-owned mixed-sequence grammar.
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh send-keys \
  '/model<[Enter]><[Down]><[Enter]>'

# Send token-like text literally instead of interpreting <[Enter]> as a keypress.
scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh \
  '/model<[Enter]>' \
  --as-raw-string

# Observe the effect separately through inspect or tmux.
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect
```

The resulting workspace is expected to preserve separate artifact families:

```text
turns/turn-001.json
turns/turn-001.events.jsonl
controls/control-001.json
controls/control-001.stdout.json
controls/control-001.stderr.log
report.json
```

## Decisions

### 1. Add a dedicated `send-keys` demo subcommand and wrapper

The demo CLI will gain a separate `send-keys` command, and the demo pack will gain a wrapper such as `send_keys.sh`. The existing `send-turn` command remains the prompt-turn surface.

The operator-facing `send_keys.sh` contract will be:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh [key-stream] <other-args>
```

where `[key-stream]` is a required positional argument. The lower-level demo `send-keys` surface will mirror that positional contract so the pack does not invent a `--sequence` flag when there is no corresponding file-based variant.

Rationale:
- Prompt turns and raw control input have different lifecycle semantics.
- A distinct command mirrors the runtime split between `send-prompt` and `send-keys`.
- Operators can reason about the tutorial more easily when "send text and expect a response" is not mixed with "inject keys and observe the UI."
- Unlike prompts, this demo workflow does not have a meaningful file-based key-stream use case, so a required positional argument is simpler and easier to teach.

Alternatives considered:
- Add `--raw`, `--control`, or similar flags to `send-turn`. Rejected because one command would then carry two incompatible meanings.
- Hide control input behind `inspect` or another generic command. Rejected because observation and action should remain separate.
- Use `--sequence` and `--sequence-file` flags. Rejected because the extra option syntax only pays for itself when multiple input sources are needed, which this wrapper does not require.

### 2. Forward the runtime sequence contract without re-parsing it in the demo layer

The demo command will accept one required positional key-stream argument plus the global `--as-raw-string` flag. The demo layer will validate only high-level command-shape concerns such as "the provided key stream is not empty."

The demo layer will not parse `<[Enter]>`, normalize key names, or duplicate the runtime allowlist. It will forward the request to `brain_launch_runtime send-keys` and let the runtime remain the source of truth for mixed-sequence parsing and token validation.

Rationale:
- The runtime already owns the grammar and error contract.
- Duplicate parsing in the demo would create drift and double maintenance.
- Keeping the demo thin makes docs and tests easier to align with the runtime behavior that operators actually experience.

Alternatives considered:
- Reimplement the mixed-sequence grammar in the demo for early validation. Rejected because it duplicates logic and creates a second failure surface.
- Restrict the demo to a curated subset such as only `Escape` and arrows. Rejected because the runtime contract is already broader and the tutorial should teach the real entrypoint.
- Add `--sequence-file`. Rejected because the design goal is an ergonomic manual-control wrapper, not a second prompt-like input mode.

### 3. Persist control-input artifacts under a dedicated `controls/` family

The workspace layout will gain a `controls/` directory alongside `turns/`. Each `send-keys` invocation will write:
- a machine-readable control record such as `controls/control-001.json`,
- captured runtime stdout such as `controls/control-001.stdout.json`, and
- captured runtime stderr such as `controls/control-001.stderr.log`.

The record will be separate from `TurnRecord` and carry fields appropriate for control input, such as the control index, agent identity, raw sequence, whether raw-string mode was requested, timestamps, exit status, result payload or result summary, and captured log paths.

`DemoState` will grow an additive `control_count` field with a default of `0`, mirroring the existing `turn_count` behavior while remaining backward-compatible for older `state.json` files that do not include the field.

Rationale:
- Control input is a real persisted action, but it is not a prompt turn and should not masquerade as one.
- A dedicated artifact family keeps the existing `turns/` and `report.json` contracts stable.
- The extra persisted metadata gives operators and tests a deterministic audit trail for what was injected.

Alternatives considered:
- Reuse `TurnRecord` and `turns/`. Rejected because control input often has no response body and would distort verify semantics.
- Introduce one generic `actions/` timeline for all demo operations. Rejected for this change because it would require a larger verification and reporting refactor than the feature needs.
- Persist only stdout/stderr logs and skip a structured control record. Rejected because tests and operators benefit from a stable, log-independent summary.

### 4. Keep `verify` and prompt-turn accounting prompt-only

`verify` will continue to read only `turns/turn-*.json` and build the same prompt-turn report. `send-keys` will not increment `turn_count`, and control-input artifacts will not be counted as turns even when they appear between prompt submissions in one session.

Rationale:
- The current maintainer contract is explicitly about prompt-turn reuse and captured responses.
- Control input is open-ended and often exploratory, which makes it a poor fit for a fixed transcript-style regression check.
- Preserving the existing report shape avoids churn in `expected_report/report.json` and related documentation.

Alternatives considered:
- Count every control-input action as a turn. Rejected because it changes the meaning of "turn" and would make the report less useful.
- Extend `verify` to summarize both turns and control actions. Rejected for the first pass because it grows the snapshot surface without improving the core regression check.

### 5. Teach control input as part of the operator workflow, not as an advanced hidden feature

The README and wrapper set will treat control input as a normal tutorial step. The main walkthrough will continue to show launch, inspection, prompt submission, and stop, but it will also add a distinct control-input step with examples such as `Escape`, menu navigation, and literal-token mode.

`inspect` remains the observation tool: after `send-keys`, operators can use tmux attach, terminal log tailing, or `inspect --with-output-text` to observe the effect.

Rationale:
- The feature matters only if operators can discover and use it from the demo pack itself.
- Keeping observation separate from key injection makes the workflow easier to debug and explain.

Alternatives considered:
- Mention control input only in a maintainer appendix. Rejected because the user-facing goal is interactive manual control, not just hidden debug tooling.
- Make `send-keys` wait for or summarize resulting UI changes. Rejected because raw control input is intentionally low-level and the right follow-up varies by provider state.

### 6. Extend integration coverage through the existing fake runtime harness

Integration tests for the demo CLI already stub `pixi run python -m gig_agents.demo.cao_interactive_full_pipeline_demo` and fake runtime subcommands. The same harness will be extended to accept `send-keys`, validate the forwarded arguments, and assert the new `controls/` artifacts and unchanged `verify` behavior.

Rationale:
- The demo behavior spans wrappers, CLI argument handling, workspace persistence, and runtime delegation.
- Reusing the current fake harness keeps tests deterministic and fast while still exercising the operator-facing workflow.

Alternatives considered:
- Limit testing to unit coverage inside the Python module. Rejected because the shell wrappers and workspace contract are part of the behavior.
- Depend on a live tmux/CAO stack for the full test matrix. Rejected because it would make the new path expensive and flaky to validate in CI.

## Risks / Trade-offs

- [Risk] Operators may expect `send-keys` to behave like `send-turn` and return a response body. -> Mitigation: keep the command name distinct, persist a control-action record, and document that observation happens via `inspect`, tmux, or subsequent prompt turns.
- [Risk] Dedicated control artifacts add another workspace directory and more persisted files to the tutorial appendix. -> Mitigation: keep the structure parallel to `turns/` and document it clearly in the README appendix.
- [Risk] Runtime validation errors for malformed key tokens will surface through the demo command. -> Mitigation: forward stderr/log paths in the control record and keep the README examples aligned with the documented runtime grammar.
- [Trade-off] A separate `controls/` model is less elegant than a unified action timeline. -> Mitigation: prefer the smaller additive design now and leave a broader timeline refactor for a future change if the demo grows more TUI-heavy.

## Migration Plan

This is an additive, repo-local demo-pack change with no external deployment dependency.

Planned migration shape:
1. Add the new CLI subcommand, control-record model, and `controls/` workspace layout in the Python demo engine.
2. Extend the shell entrypoints so operators can invoke `run_demo.sh send-keys` directly and through a dedicated wrapper.
3. Keep existing workspaces compatible by creating `controls/` lazily and defaulting any new persisted state fields.
4. Update the README and integration tests to cover the new workflow while keeping `verify` and prompt-turn snapshots stable.

Rollback strategy:
- Remove the new wrapper and `send-keys` demo command.
- Ignore or delete any `controls/` artifacts left in old workspaces.
- The existing launch, prompt, inspect, verify, and stop workflow remains intact because this change is additive.

## Open Questions

- None. The design deliberately chooses a dedicated `controls/` artifact family now and defers any broader action-timeline unification to follow-up work.
