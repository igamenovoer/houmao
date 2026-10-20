# Debug Intent: Codex Hook Observation

Date: 2026-10-20. Status: **resolved** (iteration 1 complete 2026-10-20; KQ-1 through KQ-5 resolved; all success criteria met — 12 paired captures, auto-trust verdict, payload catalog, rules demonstrated by replay with zero mismatches, E1-E4 chosen variants; iteration-2 leftovers named in the [plan](iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md)). Lane correction 2026-10-20: codex-gac measured dead (HTTP 402) at the S0 gate; switched to codex-openlux-auto, verified live same-day. Campaign directory: `context/campaigns/debug/2026-10-20-codex-hook-observation/`.

## Problem Statement

The Claude hook observation channel shipped and archived on 2026-10-20 (`openspec/changes/archive/2026-10-20-add-cli-hook-observation-channel/`). Codex is the next agent to cover. The Codex CLI source (local checkout `extern/orphan/codex`, updated to main `0910087`, 2026-10-20) shows that Codex has grown a full Claude-style hooks system since houmao's codex support was written: a dedicated `codex-rs/hooks/` crate with 14 events, stable and enabled by default since v0.124.0; the installed binary on this host is 0.163.0 and exposes `--dangerously-bypass-hook-trust` (verified in `codex --help`, 2026-10-20).

Every load-bearing fact about the Codex hooks system is so far known only from source reading, not from live traffic on this host. The riskiest difference from Claude is the trust model: a hook without a persisted `trusted_hash` is listed but silently never executed, and the interactive trust modal exists only in the TUI. A houmao-managed session is unattended; a trust modal would hang it and a silent skip would leave the channel dead without any error. The user requirement for this campaign: **hook trust must be arranged automatically at launch, with no user action, in unattended mode.**

The campaign question: before any production implementation, what is the appropriate way to inject and auto-trust houmao's observer hooks for Codex, what do the 14 events actually deliver at the installed version, and do the merged hook + TUI state-transition rules survive contact with real Codex sessions?

## Relationship to OpenSpec

No Codex hook-observation OpenSpec change exists yet. This campaign is the pre-implementation evidence phase for a future change (working name `add-codex-hook-observation`, reusing the shipped `cli-hook-observation` capability where the design ports). Findings will seed that change's proposal, design, and state-transition rules with dated, evidence-backed decisions. Production code under `src/` is not touched by this campaign.

## Starting Evidence (source-derived, 2026-10-20, all from `extern/orphan/codex` @ `0910087`)

1. Event set: `PreModelRequest`, `PostModelRequest`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`, `Interrupt` (`codex-rs/hooks/src/lib.rs:24-39`). Feature `hooks` (`Feature::CodexHooks`) is Stable and default-enabled (`codex-rs/features/src/lib.rs`).
2. Payload contract: stdin JSON is snake_case with `session_id`, `turn_id` (all except SessionStart/SessionEnd), `cwd`, `hook_event_name`, `model`, `transcript_path` (nullable), `permission_mode`; tool events add `tool_name`, `tool_input`, `tool_use_id` (except `PermissionRequest`, which has no `tool_use_id`); generated schemas at `codex-rs/hooks/schema/generated/`.
3. Trust model: handlers install only when `enabled && (bypass || managed || trusted_hash matches)` (`codex-rs/hooks/src/engine/discovery.rs:810`). Trust state merges from User and SessionFlags layers only (`codex-rs/hooks/src/config_rules.rs`). The TUI-only trust modal is at `codex-rs/tui/src/startup_hooks_review.rs`; `codex exec` and app-server skip untrusted hooks silently. `--dangerously-bypass-hook-trust` (`codex-rs/utils/cli/src/shared_options.rs:60`) bypasses hook trust for one invocation but not project trust.
4. Injection surfaces: `$CODEX_HOME/hooks.json` or `$CODEX_HOME/config.toml [hooks]` (User layer, no project trust needed); `-c 'hooks.SessionStart=[...]'` session-flags overrides; `CODEX_HOME` must exist before launch. Managed hooks (`/etc/codex/requirements.toml`) are auto-trusted but not writable by houmao; `allow_managed_hooks_only` would suppress user hooks.
5. Execution semantics: hooks run via `<shell> -c "<command>"`, stdin JSON without trailing newline; sync handlers for one event run concurrently and are awaited; `async = true` handlers cannot apply control effects and are aborted at session shutdown (lossy in `codex exec`); `SessionEnd` is forced synchronous with a 1-3 s timeout cap; other events default to 600 s. Plain stdout becomes model context on `SessionStart`/`UserPromptSubmit`/`SubagentStart` and marks the hook failed on `Stop`/`Interrupt`; a collector must exit 0 with empty stdout.
6. Terminal semantics: `Stop` fires only on normal turn completion (errors skip it); `Interrupt` fires on user abort with no reason field; `SessionEnd` is root-thread-only with constant `reason: "other"` and is not guaranteed on kill. There is no monotonic turn counter and no event timestamp; correlation is `(session_id, turn_id)` with UUIDv7 ids.
7. houmao's managed codex launches already synthesize a runtime-owned home (`config.toml` trust preseed, approval/sandbox overrides; `src/houmao/agents/launch_policy/registry/codex.yaml`), so hook injection slots into a home houmao already owns.
8. The Claude campaign (`context/campaigns/debug/2026-10-19-claude-hook-observation/`) established the paired-capture discipline, the collector/emitter/normalizer experiment layout in `scripts/explore/`, and the merged state-transition rules (`openspec/changes/archive/2026-10-20-add-cli-hook-observation-channel/design/state-transitions.md`) that this campaign replays against Codex streams.

## Comparison Arms

Implementation arms to be tried in `scripts/explore/codex-hook-observation/` (multiple variants per arm expected; this campaign is explicitly iterative):

| Arm | Approach | What is evaluated |
| --- | --- | --- |
| E1 | Auto-trust variants: (a) `--dangerously-bypass-hook-trust` launch flag, (b) pre-written `[hooks.state."<key>".trusted_hash]` via a local reimplementation of Codex's normalized-hash, (c) `-c` session-flags injection, (d) no-trust control | Which variants run hooks with zero user action in unattended TUI mode; control documents the failure mode being avoided |
| E2 | Collector transport variants: HTTP collector vs command-hook file emitter vs hybrid (reuse of the Claude lane's stdlib emitter where it ports) | Delivery reliability, ordering, latency, failure behavior |
| E3 | Normalizer and posture reducer variants against captured streams | `turn_id` correlation (vs Claude's time-window workaround), idempotency, orphan handling, `PermissionRequest` settle without `tool_use_id` |
| E4 | Merge replay variants against the archived state-transition rules | Faithfulness of hook-vs-TUI merge, compaction handling via real `PreCompact`/`PostCompact` (instead of TUI repaint heuristics), `blocked` state via `PermissionRequest` |

## Capture Matrix (user requirement: at least 5 sessions)

Minimum seven scenario sessions, each producing a paired record (hook event stream + TUI pane recording + labels). Sessions are specified with frozen prompts and predeclared expectations in iteration 1.

| Session | Scenario | Must capture |
| --- | --- | --- |
| S0 | Gate smoke: injected hooks + auto-trust, unattended start | `SessionStart` arrives; no trust modal; unattended ready reached |
| S1 | Normal multi-turn via short prompts | `SessionStart(source=startup)`, `UserPromptSubmit`, `Pre/PostModelRequest`, `Pre/PostToolUse`, `Stop` x2, clean exit `SessionEnd` |
| S2 | Trust control: hooks present, no bypass, no pre-trust | documented failure mode (modal hang or silent skip); then interactive trust-all to confirm hash path |
| S3 | Permission lane: launch without approval bypass, tool needs approval | `PermissionRequest` timing vs TUI modal paint, allow and deny outcomes, settle evidence without `tool_use_id` |
| S4 | Manual compaction mid-session (`/compact`) | `PreCompact`/`PostCompact(trigger=manual)`, `SessionStart(source=compact)`, posture continuity |
| S5 | Esc interrupt mid-turn | `Interrupt` payload; confirmation that `Stop` does NOT fire |
| S6 | Queued follow-up during a busy turn | `UserPromptSubmit` for steered/queued input; `Stop` ordering under queue drain |
| S7 | Resume/relaunch (`codex resume`) | `SessionStart(source=resume)`, new-generation `session_id` semantics, `SessionEnd` on exit |

Optional S8 (`codex exec` non-interactive mode) runs only if S0-S7 close cleanly and async-abort behavior at shutdown still needs evidence.

## Credential and Cost Lane (corrected 2026-10-20)

All live LLM-driving sessions launch through the `codex-openlux-auto` lane (`~/.local/bin/codex-openlux-auto`): it uses the `openlux-auto` profile (`$CODEX_HOME/openlux-auto.config.toml`, OpenLux relay `https://api.openlux.ai/v1`, `wire_api` per profile) and execs `codex --profile openlux-auto --dangerously-bypass-approvals-and-sandbox "$@"`. Verified live 2026-10-20 (one `codex exec` probe, rc=0). `codex-skip-all` (plain `codex` + both bypass flags) is the base for trust-arm experiments that must not use the lane profile.

Superseded lane: `codex-gac` was the predeclared primary until the S0 gate measured HTTP 402 "No active subscription" from `https://gaccode.com/codex/v1` (evidence: [S0 gate](evidences/2026-10-20-s0-gate-smoke.md)). The 402 arrived only at the model call; hook delivery (SessionStart, UserPromptSubmit, SessionEnd) worked before it, so the failed run still counts as trust-path evidence.

- The relay bills real money per token. Cost discipline: frozen short prompts per scenario, recordings reused across all analysis arms, no exploratory sessions beyond the plan.
- Session S3 (permission capture) replicates the lane's profile without the approvals bypass so the TUI approval modal actually appears.
- Credential hygiene: API keys and credential material are never read into chat, printed, copied, or embedded in artifacts; runner scripts read them at runtime from the launcher environment. Raw hook payload quotes are limited to structure and field names, plus session-authored prompt text.

## Scope and Implementation Boundary

- In scope: live captures via tmux-driven Codex TUI sessions on this host; throwaway implementations in `scripts/explore/codex-hook-observation/`; replay and fault injection against captured streams; dated amendments to this campaign's documents.
- Read-only: production code under `src/`, the launcher scripts, credential files, and the Claude campaign's frozen fixtures.
- Out of scope: production implementation (that is the future OpenSpec change, after this campaign resolves), Kimi Code hook support, `codex exec` / headless backend adoption beyond optional S8 evidence.

## Success Criteria

- At least 5 scenario sessions (target 7) captured with paired hook + TUI streams and labels, covering the matrix above.
- The auto-trust question has a definite answer: at least one injection variant demonstrably runs hooks with zero user action in unattended TUI mode at the installed version, with the trust-modal failure mode documented from the control arm.
- The payload catalog for the 14 events is confirmed or corrected per event at the installed version (0.163.0), including which events never fire in TUI mode.
- Every applicable rule from the archived `state-transitions.md` is either demonstrated against captured or fault-injected Codex streams, or marked unresolved with the missing evidence named.
- Each E1-E4 arm ends with a chosen implementation variant and evidence for the choice, recorded in a campaign report.

## No-Product-Change Declaration

This campaign is diagnostic and experimental. It authorizes captures and throwaway code under `scripts/explore/codex-hook-observation/`. It does not authorize changes to production code under `src/`, to existing tests, or to any launched provider's behavior.

## Links

- Key questions: [KQ-1](key-questions/KQ-1-unattended-trust-injection.md), [KQ-2](key-questions/KQ-2-event-availability-payloads.md), [KQ-3](key-questions/KQ-3-delivery-semantics.md), [KQ-4](key-questions/KQ-4-blocked-state-permission.md), [KQ-5](key-questions/KQ-5-merge-semantics.md)
- Iterations: [plan 1](iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md)
