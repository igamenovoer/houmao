## Context

The interactive CAO demo already has two related contracts in place:

1. startup now provisions a per-run workspace and uses that run root as the CAO trusted home by default, and
2. operators are expected to use `run_demo.sh inspect` as the advanced surface for tmux attach and log-tail commands.

Today those contracts do not line up cleanly. The demo persists `cao_profile_store` under the run-root home, but it still records `terminal_log_path` as `~/.aws/cli-agent-orchestrator/logs/terminal/<terminal_id>.log` and reprints that value in `inspect`, the README, and the verification snapshot. In real runs this produces an operator hint that looks authoritative but can point at a non-existent file because CAO is running with `HOME=<run-root>`, not with the operator's real login home.

The change is cross-cutting enough to warrant design guidance because it touches the Python demo lifecycle, the operator-facing CLI output, the README examples, the verification snapshot shape, and the corresponding tests.

## Goals / Non-Goals

**Goals:**
- Make `run_demo.sh inspect` easier for a human to scan during manual debugging.
- Ensure the interactive demo's terminal-log breadcrumb points to the actual file written by the launched CAO server.
- Surface the live Claude Code state in `inspect` without making the command depend on a perfectly healthy CAO connection.
- Support an opt-in `inspect --with-output-text <num-tail-chars>` view that shows the latest clean Claude dialog tail without exposing raw TUI/ANSI noise.
- Keep machine-readable inspection/report data coherent with the human-readable output.
- Align README examples and verification logic with the same resolved-path contract.

**Non-Goals:**
- Redesigning the interactive demo lifecycle beyond the inspect surface.
- Changing shared CAO server launcher semantics or shared runtime behavior outside this demo pack.
- Building a general-purpose log discovery system for every CAO demo in `scripts/demo/`.
- Persisting full live TUI snapshots or turning `inspect` into a transcript export command.

## Decisions

### 1. Treat the demo's effective CAO home as the source of truth for terminal log paths

The terminal log path for the interactive demo will be derived from the effective launcher home used for the local CAO server, not from the operator shell's `~`.

Rationale:
- The launcher documentation already defines that `home_dir` becomes CAO's `HOME` and that CAO state is written under `HOME/.aws/cli-agent-orchestrator/`.
- The interactive demo intentionally sets `home_dir` to the per-run workspace root by default, so the actual terminal log file lives under `<run-root>/.aws/cli-agent-orchestrator/logs/terminal/`.
- Reusing a hard-coded `~/.aws/...` breadcrumb is simple but wrong for this demo's default startup layout.

Alternatives considered:
- Keep `~/.aws/...` as a "conventional" path and only add a note explaining the mismatch. Rejected because the surface remains misleading at the exact moment an operator wants a copy-pastable command.
- Stop showing a filesystem path and only show `terminal_id`. Rejected because it makes a common debugging action less convenient and weakens the inspect surface.

### 2. Make the default `inspect` console output operator-oriented rather than state-oriented

The human-readable `inspect` output will be organized around the operator's next actions and artifact locations instead of printing a flat list of fields with equal visual weight.

Rationale:
- Operators mainly need to answer three questions quickly: "Is the session live?", "How do I attach?", and "Which file do I tail?".
- The current flat output buries the actionable commands among internal paths and timestamps.
- Grouping the data into session summary, actions, and artifact locations improves readability without removing useful metadata.

Alternatives considered:
- Keep the flat line-oriented format and only swap in the corrected log path. Rejected because it fixes correctness but not the readability complaint that triggered the change.
- Replace the JSON output with a nested human-oriented schema. Rejected because scripts and tests already rely on stable machine-readable fields.

### 3. Preserve machine-readable inspection/report fields while updating their values to the resolved path contract

The JSON/report surfaces will continue to provide stable inspection metadata, but the stored `terminal_log_path` value will represent the resolved filesystem path under the effective CAO home. New readability fields such as `claude_code_state` should be additive rather than replacing existing keys.

Rationale:
- Existing tooling already expects `terminal_log_path`, `terminal_id`, and related metadata.
- A live Claude Code state field can be added without disrupting existing consumers of the current JSON shape.
- The contract bug is about correctness, not about the need to delete those fields.
- Additive evolution keeps the implementation and tests easier to update than a wholesale schema change.

Alternatives considered:
- Break the JSON schema and introduce only a new `resolved_terminal_log_path` field. Rejected because the existing field name is still semantically correct once it contains the real path.
- Remove path assertions from the verification contract. Rejected because that would allow the mismatch to regress silently.

### 4. Resolve Claude Code state from live CAO terminal status with a best-effort fallback

`inspect` will attempt to query `GET /terminals/{terminal_id}` against the persisted `cao_base_url` and surface the returned CAO terminal status as a `claude_code_state` field in both human-readable and JSON output.

If the live lookup fails because the CAO server is unavailable, the terminal is missing, or the request otherwise cannot be completed, `inspect` should still render the persisted demo metadata and use a fallback state such as `unknown` instead of failing outright.

Rationale:
- The operator asked for Claude Code state specifically, and CAO already exposes a concrete terminal-status enum that maps well to that need.
- A best-effort lookup preserves the usefulness of `inspect` for postmortem debugging, where the persisted session metadata may still matter even if the live terminal is gone.
- The fallback keeps the advanced interface resilient while still rewarding healthy live runs with better status visibility.

Alternatives considered:
- Persist a last-known Claude state in `state.json` and only print that. Rejected because the value would go stale quickly and would not answer the operator's real-time question.
- Make `inspect` fail when status lookup fails. Rejected because it would make the debugging surface strictly worse in stale-session cases that the demo already tries to tolerate elsewhere.

### 5. Reuse the existing Claude shadow dialog projection for `--with-output-text`

The new `inspect --with-output-text <num-tail-chars>` option will fetch live CAO `output?mode=full` scrollback for the persisted terminal, run it through the existing runtime-owned Claude shadow projection, and expose the last `<num-tail-chars>` characters of the resulting clean `dialog_projection.dialog_text`.

The option is intentionally character-based rather than line-based because operators typically want a bounded copy/paste excerpt from the most recent visible conversation, and character count maps directly to terminal/UI payload size limits.

This output-tail feature remains specific to the interactive Claude CAO demo. It does not attempt to define a provider-agnostic projection API for every demo pack.

Rationale:
- The runtime already has a tested path that converts raw Claude `mode=full` output into clean projected dialog text.
- Reusing that projection avoids duplicating ANSI stripping, banner filtering, spinner dropping, and prompt-chrome removal logic inside the demo module.
- Tailing the projected dialog text gives the operator what they asked for: the clean current TUI text, not the raw tmux scrollback.

Alternatives considered:
- Print the last `N` characters from raw `mode=full` output. Rejected because it would reintroduce ANSI codes and TUI chrome that the user explicitly wants to avoid.
- Add a line-count flag instead of character count. Rejected because the requested UX is explicitly character-based and because projected dialog lines can vary widely in length.
- Read the terminal pipe log file instead of CAO `mode=full`. Rejected because the pipe log contains raw terminal data and would need another cleaning path that duplicates the runtime parser.

### 6. Keep the output-tail feature best-effort and non-raw when live projection fails

If `inspect --with-output-text` cannot fetch live scrollback or cannot produce a supported clean projection, the command should still render the base inspection metadata and include an explicit note that the output-text tail is unavailable. It should not silently fall back to raw scrollback.

Rationale:
- The optional flag asks for richer live inspection, but operators still benefit from the persisted session metadata even if the live fetch fails.
- Falling back to raw scrollback would violate the contract that this flag shows clean TUI output text.
- An explicit unavailability note keeps the surface honest and easier to debug.

## Risks / Trade-offs

- [Risk] The resolved path may differ from older snapshots or documentation that assume `~/.aws/...`. -> Mitigation: update README examples, expected report snapshots, and verification helpers in the same change.
- [Risk] Human-readable formatting can become over-specified in tests. -> Mitigation: test for required commands/fields and broad grouping intent instead of brittle full-string snapshots where possible.
- [Risk] Live state lookup can fail in stale-session or stopped-server cases. -> Mitigation: make the lookup best-effort and fall back to `claude_code_state=unknown` while still printing persisted metadata.
- [Risk] Live output projection may fail on unsupported/new Claude UI formats. -> Mitigation: reuse the runtime shadow parser, surface an explicit output-tail unavailability note, and avoid falling back to raw scrollback.
- [Risk] Operators who memorized the old path pattern may notice a behavior change. -> Mitigation: keep `terminal_id` visible and make the new absolute path explicit so the new contract is easier to trust and debug.

## Migration Plan

1. Update the demo module to compute the terminal log path from the effective CAO home used by the demo run and reuse that value in both inspect/report flows.
2. Add a best-effort live terminal-status lookup and surface it as `claude_code_state` in human-readable and JSON inspect output.
3. Add `inspect --with-output-text <num-tail-chars>` using the existing Claude shadow dialog projection over CAO `mode=full` output and expose the requested clean tail in human-readable and JSON output.
4. Reshape the default `inspect` console output around session summary, operator commands, artifact locations, and optional output-text sections.
5. Update README examples, report verification, expected snapshots, and unit tests to match the resolved-path and live-state contract.
6. Re-run the demo-level verification flow to confirm the operator-facing commands now point at real files in the per-run workspace and that opt-in clean output tails behave as expected.

Rollback is straightforward because the change is isolated to the interactive demo pack: reverting the implementation and refreshed snapshots restores the prior behavior.

## Open Questions

- None at proposal time. The design assumes the interactive demo should keep the existing JSON/report keys and only correct the path semantics plus the human-readable layout.
