# Tasks

## 1. Trust Hash and Hooks Generator

- [x] 1.1 Add `src/houmao/hook_observation/trust_hash.py` porting the campaign-validated hash (normalized identity, TOML-compatible `None` omission, recursive key-sorted compact JSON, `sha256:` prefix) with the state-key builder (`<abs hooks.json path>:<event_label>:<group>:<handler>`)
- [x] 1.2 Unit tests pinning the three upstream vectors (`fingerprint_tests.rs` fixture; the two plugin declaration hashes from `core/tests/suite/hooks.rs`) plus timeout-clamp, matcher-drop, and `additionalContextLimit` normalization cases
- [x] 1.3 Add `src/houmao/hook_observation/codex_hooks_generator.py` emitting the 14-event observer `hooks.json` (sync, 5 s timeout, SessionEnd 2 s, no matchers, emitter command) and the rendered `[hooks.state]` TOML block for a given runtime-home path, with a golden self-hash test over the generated block

## 2. Install and Gating Generalization

- [x] 2.1 Generalize `install.py` to per-adapter artifact dirs (`hook-observation/{claude,codex}`), per-tool env flags (`HOUMAO_HOOK_OBSERVATION_CLAUDE` unchanged, add `HOUMAO_HOOK_OBSERVATION_CODEX`), and `hook_observation_applies()` covering `("codex", "local_interactive")`, keeping Claude behavior byte-identical
- [x] 2.2 Add the Codex install path: write `hooks.json` into the runtime home, render and merge the Houmao-owned `[hooks.state]` entries into the runtime-home `config.toml` synthesis (idempotent, generation-scoped rewrite, removal on cleanup), degrade to `unavailable` on any unsafe write
- [x] 2.3 Unit tests for enablement gating, pre-trust block rendering/merge/removal, and degradation paths (existing Claude install tests must keep passing unmodified)

## 3. Codex Normalizer and Reducer Rules

- [x] 3.1 Add `codex_normalizer.py`: PascalCase event mapping to the provider-neutral model, `turn_id` turn epochs, steer detection (repeat `UserPromptSubmit` in the running epoch), `tool_use_id` pairing, `PermissionRequest` pair-back to the preceding `PreToolUse` (same turn, equal tool name, `tool_input.command` disambiguation), `SessionStart.source`/compact `trigger` maintenance evidence, unknown/undispatched families tolerated and counted
- [x] 3.2 Extend `reducer.py` with Codex posture rules per `design/state-transitions.md`: `Stop` success latch (defensive `stop_hook_active` continuation), `Interrupt` interrupted settlement (only override), blocked enter/settle (allow via paired `PostToolUse`, deny via `Interrupt`), compaction window hold + new epoch, terminal-gap and `SessionEnd`-with-open-turn truthful unknown, generation/resume reset
- [x] 3.3 Commit sanitized hermetic fixtures derived from the campaign streams (S1, S3, S4, S5, S6, S7, F1) and replay them in unit tests against expected timelines, mirroring the campaign's `replay_reduce.py` expectations

## 4. Launch Integration

- [x] 4.1 Generalize `hook_observation_launch.py` install dispatch per adapter (collector lifecycle, token, wrapper env, generation handling unchanged); Codex install uses the 2.2 path and never adds `--dangerously-bypass-hook-trust` to managed launch args
- [x] 4.2 Update `launch_plan.py` gating for the `("codex", "local_interactive")` pair and `HOUMAO_HOOK_OBSERVATION_CODEX`; verify the managed canonicalizer preserves the launch-owned hook config (resolve the design's open question on `hooks.*` `-c` keys with a test either way)
- [x] 4.3 Update `registry/codex.yaml`: document owned `hooks.state.*` keys and `hooks.json` presence, evidence refs (campaign + source), and the version-floor note that hooks are stable across the supported range
- [x] 4.4 Launch-policy tests: synthesized runtime home contains hooks.json + pre-trust block, wrapper env carries token/collector coordinates (never `plan.env`), relaunch allocates a new generation and rewrites the block

## 5. Tracker Merge

- [x] 5.1 Extend `server/tui/tracking.py` merge for the Codex adapter: hook-derived `interrupted` for Codex sessions only (Claude unchanged), blocked entry/settle per the Codex rules, compaction-window suppression of TUI idle heuristics, terminal-gap publication
- [x] 5.2 Unit tests over the merged tracker: Codex Esc interrupt, deny-abort, compaction continuity, kill-gap, and a Claude regression proving interrupted stays TUI-derived there
- [x] 5.3 Confirm gateway prompt admission treats Codex `blocked` correctly with no admission-policy change (test only; the policies are already generic)

## 6. Recorded Replay and Live Qualification

- [x] 6.1 Recorded validation: `pixi run test` and `pixi run typecheck` green, including the 3.3 fixture replays
- [x] 6.2 Live smoke (opt-in flag, codex-openlux-auto lane, frozen short prompts): multi-turn success, permission-lane allow/deny with `blocked` visible on tracked state, Esc interrupt, compaction, kill-gap; verify tracked state, channel health, and secret-free public projection for each
- [x] 6.3 Floor repeat of the multi-turn smoke at the lowest supported Codex version from `codex.yaml` (side-by-side install), or a named gap if the floor cannot be installed

## 7. Documentation

- [x] 7.1 Update the hook observation reference docs for the Codex adapter (event set, trust model, enablement flag, degradation behavior)
- [x] 7.2 Update the launch-policy reference for the new codex owned keys and the pre-trust mechanism
- [x] 7.3 Update AGENTS.md-facing or developer docs that enumerate the observation channel's provider coverage

## Workflow follow-up

- [x] 8.1 During apply, keep `scripts/explore/codex-hook-observation/` frozen as campaign evidence; port (never import) from it, and record any upstream drift found via the trust-hash fixture tests as a dated note in the campaign directory
