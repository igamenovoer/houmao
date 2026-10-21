# Tasks

## 1. Kimi Hooks Generator (config.toml `[[hooks]]` block)

- [x] 1.1 Add `src/houmao/hook_observation/kimi_hooks_generator.py`: render the 20-event observer block (one `[[hooks]]` entry per event, matcher omitted, timeout 5 s, absolute emitter command shell-quoted), merge it marker-delimited into a runtime-home `config.toml` (idempotent, generation-scoped rewrite, removal support, pre-existing content preserved byte-identical outside the block), and validate any merged file by strict `tomllib` read-back (keys subset of `{event, matcher, command, timeout}`, event in the pinned 20-name enum, timeout int in 1..600) raising on any violation
- [x] 1.2 Unit tests for the generator: golden block rendering, merge into a config carrying launch-policy-owned fields (coexistence diff clean in both write orders — settles campaign leftover P1.4), idempotent rewrite, teardown removal, and validation refusal for each malformed class (extra key, unknown event, bad timeout)

## 2. Install and Gating Extension

- [x] 2.1 Extend `install.py` for the Kimi adapter: `HOUMAO_HOOK_OBSERVATION_KIMI` env flag, `("kimi", "local_interactive")` in `HOOK_OBSERVATION_PAIRS`, `kimi` entry in `ADAPTER_DIRNAMES` (`store.py`), keeping Claude and Codex behavior byte-identical
- [x] 2.2 Add the Kimi install path: merge + strict-validate the observer block into the launch-owned runtime home's `config.toml` via `kimi_hooks_generator.py`, degrade to `unavailable` on any validation or write failure without failing the launch, remove the block on channel cleanup
- [x] 2.3 Unit tests for Kimi enablement gating, block install/merge/removal, validation-failure degradation, and cleanup (existing Claude and Codex install tests must keep passing unmodified)

## 3. Kimi Normalizer and Reducer Rules

- [x] 3.1 Add `kimi_normalizer.py`: PascalCase event mapping to the provider-neutral model, ContentPart[] `prompt` collapse to joined text (raw shape in diagnostics), two-phase arm/bind turn correlation (`UserPromptSubmit` arms, `TurnStarted` binds the integer session-scoped `turn_id`), ordering-based attribution for tool events and `Stop` (no `turn_id` on them), `tool_call_id` tool pairing, `UserPromptQueued` queue evidence without a second prompt-submit, subagent nested scopes (`SubagentStart`/`SubagentStop`, nested `TurnStarted`), `SessionHeartbeat` as liveness evidence, unknown/silent families tolerated and counted
- [x] 3.2 Extend `reducer.py` with Kimi posture rules per `design/state-transitions.md`: `Stop` success latch (defensive `stop_hook_active` continuation), `Interrupt(reason=cancelled)` interrupted settlement, blocked enter at `PermissionRequest` and settle at `PermissionResult` for both decisions (deny → non-terminal `PostToolUseFailure`, turn continues to `Stop`), compaction window hold + fresh post-compact epoch (no `SessionStart(source=compact)`), terminal-gap and `SessionEnd`-with-open-turn truthful unknown, `headless_session_end_gap` diagnostic, generation/resume reset with continuing `turn_id` counter
- [x] 3.3 Extend `reader.py` normalizer selection for adapter `kimi`, and commit sanitized hermetic fixtures derived from the campaign streams (S0, S1, S3, S4, S5, S6, S7, F1, D1) replayed in unit tests against expected timelines, mirroring the campaign's `replay_reduce.py` expectations
- [x] 3.4 Unit tests mirroring the Codex adapter's suites: `test_kimi_hooks_generator.py`, `test_kimi_normalizer.py`, `test_kimi_reducer.py`, kimi fixtures, plus kimi cases in `test_install.py`/`test_reader.py`/`test_store.py`

## 4. Launch Integration

- [x] 4.1 Extend `hook_observation_launch.py` install dispatch with the Kimi branch (merge + validate + cleanup); collector lifecycle, token, wrapper env, and generation handling unchanged
- [x] 4.2 Open the `launch_plan.py` adapter gate to kimi (`{"claude", "codex"}` early-out removed); verify the kimi launch canonicalizers (`canonicalize_kimi_*`) never touch `config.toml` `[[hooks]]` entries, with a regression test either way (design D8)
- [x] 4.3 Update `registry/kimi.yaml`: document the Houmao-owned `[[hooks]]` observer block in `config.toml`, evidence refs (campaign + `extern/orphan/kimi-code` source), and the version-floor note (full payload contract since upstream 0.32.0, below the 2.1.1 floor)
- [x] 4.4 Launch-policy tests: synthesized runtime home contains the validated observer block alongside launch-policy-owned fields, wrapper env carries token/collector coordinates (never `plan.env`), relaunch allocates a new generation and rewrites the block, teardown removes it; mirror the codex registry content test for kimi.yaml

## 5. Tracker Merge

- [x] 5.1 Extend `server/tui/tracking.py` merge for the Kimi adapter: `_HOOK_ADAPTER_BY_TOOL["kimi"]`, hook-derived `interrupted` for Kimi sessions only (Claude stays TUI-derived), blocked enter/settle per the Kimi rules (settle at `PermissionResult`), compaction-window suppression of TUI idle heuristics, terminal-gap publication; decide each existing codex-only branch for kimi per the design (liveness-lost, TUI interrupt evidence, terminal-gap reason, maintenance hold, `tui_interrupt_authority`)
- [x] 5.2 Unit tests over the merged tracker: Kimi Esc interrupt, permission allow/deny windows, compaction continuity, kill-gap, queue/steer, resume generation, plus a Claude regression proving interrupted stays TUI-derived there and a Codex regression proving deny still aborts there
- [x] 5.3 Confirm gateway prompt admission treats Kimi `blocked` correctly with no admission-policy change (test only; the policies are already generic)

## 6. Recorded Replay and Live Qualification

- [x] 6.1 Recorded validation: `pixi run test`, `pixi run lint`, and `pixi run typecheck` green, including the 3.3 fixture replays
- [x] 6.2 Live smoke (`tests/manual/manual_kimi_hook_observation_smoke.py`, mirroring the codex smoke, secret-free): managed-launch multi-turn success, Esc interrupt, compaction, kill-gap; verify tracked state, channel health, and secret-free public projection for each. The kimi auth bundle `tests/fixtures/auth-bundles/kimi/personal-a-default/` is host-local and absent on some machines — gate on its presence (preflight-fail with a clear message, per the bundle README) or support the campaign's seeded-scratch-home lane; a machine without either credential source records a named gap
- [x] 6.3 Floor repeat of the multi-turn smoke at the lowest supported kimi version from `kimi.yaml` (side-by-side install), or a named gap if the floor cannot be installed

## 7. Documentation

- [x] 7.1 Update the hook observation reference docs (`docs/developer/houmao-server/state-tracking.md`, `state-reference.md`, `state-transitions.md`) for the Kimi adapter: event set, no-trust install model, enablement flag, degradation behavior, kimi-specific settle rules
- [x] 7.2 Update the launch-policy reference (`docs/reference/build-phase/launch-policy.md`) and gateway contract docs (`docs/reference/gateway/contracts/protocol-and-state.md` adapter enumeration) for the kimi owned `[[hooks]]` surface and `HOUMAO_HOOK_OBSERVATION_KIMI`
- [x] 7.3 Add `docs/developer/tui-parsing/kimi-signals.md` (or the kimi section alongside `claude-signals.md`/`codex-signals.md`) describing the kimi hook adapter contract and its interaction with the 2.1.x detector profile

## 8. Campaign Hygiene

- [x] 8.1 During apply, keep `scripts/explore/kimi-hook-observation/` frozen as campaign evidence; port (never import) from it, and record any upstream drift found (event renames, schema changes at the supported floor) as a dated note in the campaign directory
