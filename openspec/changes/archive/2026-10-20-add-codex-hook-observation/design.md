# Design

## Context

The `cli-hook-observation` capability is in production for Claude: `src/houmao/hook_observation/` (collector, emitter, store, health, reader, normalizer, reducer, settings generator, install) plus launch lifecycle in `src/houmao/agents/realm_controller/hook_observation_launch.py` and the tracking merge in `src/houmao/server/tui/tracking.py`. The install/gating surface is Claude-branded (`HOUMAO_HOOK_OBSERVATION_CLAUDE`, `claude_hook_artifact_dir`, `hook_observation_applies(tool="claude", backend="local_interactive")`).

The 2026-10-20 campaign (`context/campaigns/debug/2026-10-20-codex-hook-observation/`) established against codex-cli 0.163.0: hooks are stable and default-on; 10 of 14 events fire in TUI mode; trust is mandatory and fully automatable; the payload catalog, settle rules, and 10 dated rule amendments are recorded in the campaign report and KQ answers. The supported Codex floor (`src/houmao/agents/launch_policy/registry/codex.yaml`: `>=0.162.1`) already includes stable hooks, so every supported version can carry the channel.

## Goals / Non-Goals

**Goals:**

- Managed Codex `local_interactive` sessions get the hook observation channel with automated, zero-user-action trust.
- One provider-neutral channel core; per-adapter generator, normalizer, and posture rules.
- Codex hook posture merges into tracked state per the campaign-validated rules, including hook-derived `interrupted` for Codex.
- The trust hash is a tested production component, pinned to Codex's own published test vectors.

**Non-Goals:**

- `codex exec` / headless backends, app-server hook injection, plugin hooks.
- Subagent events, `apply_patch` payload specialization, model-request events (unavailable at the floor), token-usage surfacing.
- Changing Claude adapter behavior (Claude interrupted stays TUI-derived).
- The campaign's deferred reliability arms (hung-collector, async loss) — sync short-timeout configuration is adopted as-is.

## Decisions

### D1: Injection is runtime-home `hooks.json` + synthesized pre-trust; no bypass flag on the managed path

The managed launch writes the observer `hooks.json` into the runtime-owned `CODEX_HOME` and appends Houmao-owned `[hooks.state."<abs hooks.json path>:<event>:0:0"]` entries with `trusted_hash` values into the runtime-home `config.toml` synthesis it already owns (the same `toml.set` surface that seeds project trust). This is the campaign's E1 decision: least privilege (no blanket `--dangerously-bypass-hook-trust`; only the exact vetted commands run), zero user action, and no trust modal is ever triggered. Alternatives considered: the bypass flag (tested fallback, kept documented for manual lanes; rejected as default because it disables trust for all hooks in the invocation); `-c hooks.*` session-flags injection (works raw, but managed-path canonicalization is unverified and it scatters configuration across the command line); managed `/etc/codex` layer (not writable by Houmao).

### D2: The trust hash is a production module pinned to upstream test vectors

`src/houmao/hook_observation/trust_hash.py` ports the campaign's `hash_hook.py`: normalized identity (snake_case event label, matcher kept only for matcher-capable events, timeout normalization with the SessionEnd/Interrupt 1-3 s clamp, `commandWindows` cleared, `additionalContextLimit` only for context-capable events and only when non-default), TOML-compatible serialization with `None` fields omitted, recursive key-sorted compact JSON, SHA-256 with `sha256:` prefix. Tests pin the three upstream vectors (`fingerprint_tests.rs`, plus the two plugin declaration hashes in `core/tests/suite/hooks.rs`) and a golden self-hash of the generated observer block, so an upstream algorithm change fails CI before it silently disables hooks in production.

### D3: One channel core, per-adapter generator/normalizer/applicability

Collector, store, health, reader, emitter transport, and launch-collector lifecycle are reused unchanged. Per-adapter pieces: `codex_hooks_generator.py` (14-event `hooks.json`: sync, 5 s timeout, SessionEnd 2 s, no matchers), `codex_normalizer.py`, Codex posture rules in the reducer, adapter-scoped artifact dirs (`<session_root>/hook-observation/codex/`), and per-tool env flags. `hook_observation_enabled()`/`hook_observation_applies()` generalize to `(tool, backend)` pairs: `("claude", "local_interactive")` under `HOUMAO_HOOK_OBSERVATION_CLAUDE`, `("codex", "local_interactive")` under `HOUMAO_HOOK_OBSERVATION_CODEX`. The launch lifecycle module keeps one code path parameterized by adapter, not a second copy.

### D4: Subscribe all 14 events; tolerate silent families

The observer subscribes every Codex event (sync, short timeouts, exit-0-silent emitter) including `PreModelRequest`/`PostModelRequest` (never dispatched at 0.163.0, and excluded from its trust-review set — pre-trusting them is harmless) and the subagent pair (unexercised). This keeps the configuration forward-compatible; the normalizer counts unseen/unknown families in diagnostics instead of failing. The emitter contract is identical to Claude's: read stdin to EOF, POST-or-file-fallback, always exit 0, empty stdout (non-empty stdout pollutes model context on some Codex events and marks the hook failed on Stop/Interrupt).

### D5: Codex normalizer maps to the provider-neutral model via `turn_id` epochs

Event names arrive PascalCase with the same envelope conventions as Claude plus Codex extensions. Turn correlation uses `turn_id` directly — no time-window heuristic. A second `UserPromptSubmit` carrying the running turn's `turn_id` is a steer, not a new turn. Tool cycles pair `PreToolUse`/`PostToolUse` by `tool_use_id`. `PermissionRequest` has no `tool_use_id`: it pairs back to the immediately preceding `PreToolUse` in the same `turn_id` with equal `tool_name`, disambiguated by `tool_input.command` equality (validated one-to-one across two approval cycles in one session). `SessionStart.source` ∈ {startup, resume, compact, clear, fork} and compact `trigger` ∈ {manual, auto} map to maintenance evidence. Unknown names/fields are tolerated and counted, per the existing provider-neutral requirement.

### D6: Codex posture rules follow the campaign amendments

Full rules live in [`design/state-transitions.md`](design/state-transitions.md). Headline: `Stop` latches turn success (defensive `stop_hook_active` continuation handling); `Interrupt` settles `interrupted` and is the only override of a latched terminal; `PermissionRequest` enters `blocked`, settling on the paired `PostToolUse` (allow) or `Interrupt` (deny — at 0.163.0 deny aborts the whole turn); `PreCompact`/`PostCompact` delimit a maintenance window that holds posture and suppresses TUI idle heuristics, with the post-compact turn starting a new epoch; steered input stays in the running epoch; stream end without `Stop`/`Interrupt`/`SessionEnd`, or `SessionEnd` with an open turn, is a terminal gap — presence lost, turn truthfully `unknown`, never success.

### D7: Hook-derived `interrupted` for Codex only

The tracked-state spec currently requires `interrupted` to remain TUI-derived with no hook settlement. Codex's `Interrupt` is authoritative (Esc, approval-deny, extension abort all fire it within ~50-65 ms of the cause; the TUI merely repaints afterward). The delta MODIFIES `official-tui-state-tracking` so hook `Interrupt` settles `interrupted` when a Codex channel is active, while Claude sessions keep TUI-derived interrupted (Claude has no Interrupt event; its `silent_abort_idle` heuristics remain load-bearing there). Gateway prompt admission already treats `blocked` generically and needs no change.

### D8: Launch wiring reuses the existing collector lifecycle; Codex policy gains install actions

`hook_observation_launch.py` generalizes its install step per adapter: for Codex, write `hooks.json` into the runtime home, render the `[hooks.state]` block from the generated handlers, and let the existing collector start/token/wrapper machinery run unchanged (token and collector coordinates travel in the launch wrapper env, never `plan.env`). `registry/codex.yaml` documents the new owned keys (`hooks.state.*`, `hooks.json` presence) and evidence. Relaunch/resume semantics match Claude: new channel generation per provider start; live collector adoption on control-plane resume; collector stop on session stop.

### D9: Degradation mirrors Claude; hash drift is detected by event silence

Any install/collector failure degrades to `unavailable` and the session launches TUI-only. If a provider upgrade changes the hash algorithm or the event set, Codex silently skips the untrusted handlers; the channel detects this as startup event silence (no `SessionStart` at first turn within the grace) plus collector liveness, reports `degraded`, and preserves TUI-only behavior. The D2 fixture tests are the early-warning tripwire in CI.

### D10: The `work` axis stays `unknown` for Codex

Codex `Stop` has no `background_tasks` mirror and no background-work feature was exercised at 0.163.0 (campaign P5.4). The channel publishes `work=unknown` and does not claim `settled` from hooks alone; if Codex later exposes task lifecycle evidence, a follow-up change adds the clearing rule.

## Risks / Trade-offs

- Upstream changes the trust hash algorithm → hooks silently skipped → D2 fixture tests fail in CI at the supported floor; runtime detection via D9 event silence; emergency manual lane via the documented bypass flag.
- Provider kills/crashes leave no terminal event → truthful `unknown` (D6) instead of a fabricated outcome; consumers must tolerate `unknown` (already part of the axis contract).
- Two parallel tool calls requesting approval in one turn could interleave `PreToolUse`/`PermissionRequest` → pair-back rule uses `tool_input.command` equality and falls back to turn-scoped ambiguity (blocked without tool attribution) rather than mispairing.
- Codex's trust-all writes state into the active profile file, not `config.toml` → managed sessions never rely on interactive trust; profile refreshes do not clobber the synthesized `config.toml` block.
- Subscribing non-firing events couples the observer block to upstream event renames → version-gated event selection (existing requirement) pins the subscribed set per supported floor; unknown names are tolerated.

## Migration Plan

No data migration. The channel is opt-in per adapter via `HOUMAO_HOOK_OBSERVATION_CODEX=1`; without it, Codex sessions are byte-identical to today. Rollback is unsetting the flag; the observer block and pre-trust entries live only in the per-session runtime home.

## Open Questions

- Whether the managed launch's caller-override canonicalization needs an explicit allow for `hooks.*` `-c` keys (campaign named leftover; resolved during launch-policy implementation by reading the canonicalizer's owned-surface list, with a test either way).
- Whether 0.162.x floors dispatch the identical event set as 0.163.0 (the campaign measured 0.163.0 only; a floor-repeat of the S1 capture is part of the qualification tasks).
