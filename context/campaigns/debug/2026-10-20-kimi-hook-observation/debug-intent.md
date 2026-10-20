# Debug Intent: Kimi Code Hook Observation

Date: 2026-10-20. Status: **resolved** (2026-10-20): capture and replay phases complete; 13 arms / 16 launches captured, 18 run roots replayed, KQ-1..KQ-5 answered, E1-E4 variants settled, synthesis report written to `reports/2026-10-20-kimi-hook-observation-synthesis.md`. Named leftovers need new live evidence (see the report), not another pass over these captures. Campaign directory: `context/campaigns/debug/2026-10-20-kimi-hook-observation/`.

## Problem Statement

The Claude hook observation channel and the Codex adapter both shipped and archived on 2026-10-20 (`openspec/changes/archive/2026-10-20-add-cli-hook-observation-channel/`, `openspec/changes/archive/2026-10-20-add-codex-hook-observation/`). Kimi Code is the third managed CLI agent. The Kimi Code source (local checkout `extern/orphan/kimi-code`, updated to main `67325c1`, 2026-10-20) shows a native hooks system: one engine at `packages/agent-core-v2/src/features/externalHooks/`, 20 events, configured via `[[hooks]]` entries in `$KIMI_CODE_HOME/config.toml`, with **no trust gate** — hooks run unattended with zero interactive prompts (source reading plus grep over the feature, 2026-10-20). The installed binary on this host is kimi 2.2.0 (`kimi --version`, verified 2026-10-20).

Every load-bearing fact is so far known only from source reading, not from live traffic on this host. The kimi-specific risks differ from Codex (where the trust modal dominated):

1. The `[[hooks]]` config schema is **strict** (`event`, `matcher`, `command`, `timeout` only), and one malformed entry voids the *entire* hooks section with a warning diagnostic only — a silent-death failure mode an installer must detect (`features/externalHooks/configSection.ts:10-17`, `app/config/configService.ts:739-758`).
2. `SessionStart`/`SessionEnd` (and `PreCompact`, `SubagentStart`) hooks are **awaited** during session create/close, so a slow observer delays the session lifecycle (`sessionExternalHooksService.ts:63-82`).
3. `PermissionRequest`/`PermissionResult` fire only when the permission policy resolves to `ask` (`toolApprovalService.ts:101-145`); houmao's unattended TUI strategy sets `default_permission_mode=auto` (`src/houmao/agents/launch_policy/registry/kimi.yaml:111-123`), so the permission lane may be unobservable in the configuration houmao actually launches.
4. `UserPromptSubmit.prompt` is a **raw ContentPart[] array**, not a string (`agentExternalHooksService.ts:337-351`) — unlike both Claude and Codex payloads.
5. Any stdout from a `UserPromptSubmit` hook on the allow path is appended to the model context (`internal/userPrompt.ts:22-73`) — a noisy observer corrupts prompts.

The campaign question: before any production implementation, what is the appropriate way to inject houmao's observer hooks into a kimi launch, what do the 20 events actually deliver at 2.2.0 across the modes houmao uses (unattended `--auto` TUI, ask-mode TUI, headless `-p`), and do the merged hook + TUI state-transition rules survive contact with real kimi sessions?

## Relationship to OpenSpec

No kimi hook-observation OpenSpec change exists yet. This campaign is the pre-implementation evidence phase for a future change (working name `add-kimi-hook-observation`, reusing the shipped `cli-hook-observation` capability where the design ports, mirroring how `add-codex-hook-observation` reused it). Findings will seed that change's proposal, design, and state-transition rules with dated, evidence-backed decisions. Production code under `src/` is not touched by this campaign.

## Starting Evidence (source-derived, 2026-10-20, all from `extern/orphan/kimi-code` @ `67325c1` unless noted)

1. Event set: 20 events in `HOOK_EVENT_TYPES` — `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionResult`, `UserPromptSubmit`, `UserPromptQueued`, `TurnStarted`, `Stop`, `StopFailure`, `Interrupt`, `SessionStart`, `SessionEnd`, `SessionHeartbeat`, `SubagentStart`, `SubagentStop`, `TaskStarted`, `PreCompact`, `PostCompact`, `Notification` (`features/externalHooks/internal/types.ts:3-24`).
2. Payload contract: stdin JSON, top-level keys snake_cased; base `{hook_event_name, session_id, cwd}` (`internal/matchHooks.ts:60-65`) plus `client_type` (`kimi_code_cli` for all in-repo hosts) and per-event `session_title`. Correlation ids: `tool_call_id` on tool and permission events; `turn_id` on `TurnStarted`/`PermissionRequest`/`PermissionResult`/`Interrupt` only — **not** on `PreToolUse`/`PostToolUse` (a correlation difference from Codex). No `transcript_path`; `model`/`profile` only on `SessionStart`. Session files persist under `$KIMI_CODE_HOME/sessions/`.
3. Config resolution: single user-level `$KIMI_CODE_HOME/config.toml`; home = `KIMI_CODE_HOME` env else `~/.kimi-code` (`app/bootstrap/bootstrap.ts:168-174`). Strict schema rejects extra keys; one bad entry drops the whole section with a warning. Hooks load **once per process**; mid-session config edits do not reload (`app/externalHooksRunnerService.ts:37-41`).
4. No trust gate: no approval, allowlist, or hash anywhere in the feature; no config/env off switch other than removing entries. Hooks fire identically in TUI, `kimi -p`, ACP, and kap-server modes.
5. Execution semantics: command runs via system shell, stdin = one JSON object (no trailing newline), env inherited from the engine process, cwd = session project dir. Exit 0 = allow, 2 = block, other = fail-open allow; timeouts SIGTERM then SIGKILL the process group after 100 ms. Observation-event results are discarded, but blockable events (`PreToolUse`, `Stop`, `UserPromptSubmit`) honor exit-2 / `hookSpecificOutput.permissionDecision="deny"`.
6. Version floor: enriched payloads (`session_title`, `client_type`, `TurnStarted`, `TaskStarted`, `SessionHeartbeat`) landed in upstream 0.32.0 (2026-08-04); houmao's registry floor is `>=2.1.1`, so every supported version carries the full contract. Installed: 2.2.0 (2026-10-14, latest released). One unreleased patch at the pin (`.changeset/hooks-session-cwd.md`) fixes hook cwd for server-started sessions; the TUI lane starts in the project dir already.
7. houmao's managed kimi launches already own fields in `config.toml` (`default_model`, providers, models, `default_permission_mode`) and the `KIMI_CODE_HOME` env var (`src/houmao/agents/launch_policy/registry/kimi.yaml`), so hook injection slots into a home houmao already controls; the installer must merge, not rewrite.
8. The Claude and Codex campaigns (`context/campaigns/debug/2026-10-19-claude-hook-observation/`, `context/campaigns/debug/2026-10-20-codex-hook-observation/`) established the paired-capture discipline, the collector/emitter harness layout in `scripts/explore/` (the Codex harness ports almost verbatim — no trust hash needed for kimi), and the merged state-transition rules this campaign replays against kimi streams.

## Comparison Arms

Implementation arms to be tried in `scripts/explore/kimi-hook-observation/` (multiple variants per arm expected; this campaign is explicitly iterative):

| Arm | Approach | What is evaluated |
| --- | --- | --- |
| E1 | Injection variants: (a) `[[hooks]]` TOML merge into a seeded scratch `KIMI_CODE_HOME` (expected winner), (b) malformed-entry control (documents the silent-death failure mode), (c) hot-reload probe (mid-session append; load-once verdict) | Which injection shape runs all 20 events unattended with zero user action, and how each failure mode presents |
| E2 | Collector transport variants: HTTP collector vs command-hook file fallback (reuse of the Codex lane's stdlib collector/emitter where it ports) | Delivery reliability, ordering, latency, failure behavior |
| E3 | Normalizer and posture reducer variants against captured streams | `session_id`/`turn_id`/`tool_call_id` correlation without `turn_id` on tool events, ContentPart[] prompt handling, idempotency, orphan handling |
| E4 | Merge replay variants against the archived state-transition rules | Faithfulness of hook-vs-TUI merge against the kimi 2.1.x detector, real `PreCompact`/`PostCompact`, `blocked` via `PermissionRequest`, `interrupted` via `Interrupt` |

## Capture Matrix (user requirement: at least 5 sessions)

Core scenario sessions, each producing a paired record (hook event stream + TUI pane recording + labels). Sessions are specified with frozen prompts and predeclared expectations in iteration 1. `--auto` arms are unattended; S3 is tmux-driven ask-mode (no operator action — keystrokes come from the driver).

| Session | Scenario | Must capture |
| --- | --- | --- |
| S0 | Gate smoke: seeded scratch home + 20-event `[[hooks]]`, `kimi --auto` in tmux | `SessionStart(source=startup)` arrives (awaited at create — timing vs codex's lazy dispatch); no prompts or modals; unattended ready reached |
| S1 | Normal multi-turn via short prompts, session held ≥65 s | `UserPromptSubmit` (ContentPart[] shape), `TurnStarted`, `Pre/PostToolUse` (forced `Bash` call), `Stop` x2, `SessionHeartbeat` cadence + `uptime_ms`, clean-exit `SessionEnd(reason=exit)` |
| S2 | Malformed-config control: one `[[hooks]]` entry with an extra key | Whole hooks section dropped; where the warning is visible (print-mode stderr vs TUI); channel dead with no error |
| S3 | Permission lane: default (ask) mode, no `--auto`; driver approves once, denies once | `PermissionRequest`/`PermissionResult` payloads + `decision` values; `tool_call_id` pairing; deny-path follow-up event (or absence); contrast with their total absence under `--auto` |
| S4 | Manual compaction mid-session (`/compact`) | `PreCompact`/`PostCompact(trigger=manual)`, `token_count` fields, posture continuity |
| S5 | Esc interrupt mid-turn | `Interrupt(turn_id, reason=cancelled)`; confirmation that `Stop` does NOT fire |
| S6 | Queued follow-up during a busy turn | `UserPromptQueued(prompt_id, queue_length)`; drain ordering; `is_steer` on the eventual `UserPromptSubmit` |
| S7 | Resume/relaunch (`kimi --continue`, same scratch home) | `SessionStart(source=resume)`; session_id semantics across generations; fold in E1c hot-reload probe (append marker hook before relaunch; fires only after restart) |
| S8 | Headless probe: `KIMI_CODE_HOME=<scratch> kimi -p` (no tmux) | Hooks fire in print mode; which events appear; config warnings visible on stderr |
| F1 | Fault: `kill -9` the kimi process tree mid-turn | Exactly which events do NOT arrive (no `Stop`/`Interrupt`/`SessionEnd`); heartbeat cessation; terminal-gap signature |
| D1 | Transport fault: collector killed after `SessionStart` | Emitter file-fallback engages; session unaffected (fail-open); ordering via emitter sequence |
| T1 | Slow-hook arm: `SessionStart`/`SessionEnd` hooks with `sleep 3` | Awaited lifecycle delay quantified (time-to-ready vs S0 baseline; exit delay); timeout SIGTERM/SIGKILL behavior if exceeded |
| S9 (optional) | Subagent prompt (Task tool) | `SubagentStart`/`SubagentStop` (`agent_name`, prompt/response); `TaskStarted(kind=agent)`; `Notification(task.*)` if a background task is used |

## Credential and Cost Lane

Live sessions drive the operator's real Kimi credentials, seeded into a scratch `KIMI_CODE_HOME` under `tmp/kimi-hook-capture/` by **copying** `config.toml`, `credentials/`, `oauth/`, and `device_id` from `~/.kimi-code` at runtime (`cp`, never through chat). The real `~/.kimi-code` is copy-from-only and is never modified. The host-local auth bundle `tests/fixtures/auth-bundles/kimi/personal-a-default/` does not exist on this host (verified 2026-10-20); this campaign does not need it because it drives `kimi` directly rather than through houmao's managed launch.

- The provider bills real money per token. Cost discipline: frozen short prompts per scenario, recordings reused across all analysis arms, no exploratory sessions beyond the plan. T1 and the S2 control cost zero tokens (no model call needed); F1/D1 cost one turn at most.
- Version pinning: the launch wrapper exports `KIMI_CODE_NO_AUTO_UPDATE=1` so the binary cannot self-update mid-campaign.
- Credential hygiene: API keys and OAuth material are never read into chat, printed, copied into evidence docs, or embedded in artifacts; the seeding happens inside runner scripts at runtime. Raw hook payload quotes in evidence docs are limited to structure and field names, plus session-authored prompt text. Scratch homes and run roots may contain credential material and hook payloads; treat `tmp/kimi-hook-capture/` as sensitive campaign evidence (gitignored).

## Scope and Implementation Boundary

- In scope: live captures via tmux-driven kimi TUI sessions and `kimi -p` probes on this host; throwaway implementations in `scripts/explore/kimi-hook-observation/`; replay and fault injection against captured streams; dated amendments to this campaign's documents.
- Read-only: production code under `src/`, the operator's real `~/.kimi-code` (copy-from only), the kimi source checkout `extern/orphan/kimi-code`, and the Claude/Codex campaigns' frozen fixtures.
- Out of scope: production implementation (that is the future OpenSpec change, after this campaign resolves), houmao managed-launch integration testing (the launch-policy merge shape is recorded as evidence, not wired into `src/`), kap-server/ACP-mode hook behavior beyond what the source already settles.

## Success Criteria

- At least 5 scenario sessions (target 12 arms) captured with paired hook + TUI streams and labels, covering the matrix above.
- The injection question has a definite answer: the `[[hooks]]` merge variant demonstrably runs all subscribed events with zero user action in unattended `--auto` TUI mode at 2.2.0, with the malformed-entry and hot-reload failure modes documented from the control arms.
- The payload catalog for the 20 events is confirmed or corrected per event at the installed version (2.2.0), including which events never fire in `--auto` TUI mode (permission events expected absent) and which are unexercised.
- Every applicable rule from the archived `state-transitions.md` lineage is either demonstrated against captured or fault-injected kimi streams, or marked unresolved with the missing evidence named.
- Each E1-E4 arm ends with a chosen implementation variant and evidence for the choice, recorded in a campaign report.
- A working capture/replay implementation exists in `scripts/explore/kimi-hook-observation/` and was verified with tmux pane recordings.

### Resolution (2026-10-20)

All six criteria are met. 13 arms / 16 launches produced paired hook + TUI streams at 5 fps with same-day labels (18 run roots replayed; 14 with streams and 4 controls/deviations). The E1 injection answer is the marker-delimited `[[hooks]]` append with strict read-back; S2 documents the silent whole-section drop and S1/S7 document load-once. The 20-event catalog is confirmed or corrected, with availability by mode and unexercised families named. P5.1-P5.5 are answered with one replay-exposed correction (S7 `turn_id` continues at 1, not 0) and the missing evidence for the leftovers named. E1-E4 each have a chosen variant in the [synthesis report](reports/2026-10-20-kimi-hook-observation-synthesis.md). `replay_reduce.py --self-test` passes 12/12 and `--all` passes over all 18 campaign roots with 0 label mismatches; the capture harness G0 passed 19/19.

The campaign is diagnostic; no production code, tests, or provider behavior was changed. The unresolved items are provider behaviors that require new live evidence, not unmet campaign criteria.

## No-Product-Change Declaration

This campaign is diagnostic and experimental. It authorizes captures and throwaway code under `scripts/explore/kimi-hook-observation/` and scratch state under `tmp/kimi-hook-capture/`. It does not authorize changes to production code under `src/`, to existing tests, or to any launched provider's behavior.

## Links

- Key questions: [KQ-1](key-questions/KQ-1-config-injection-coexistence.md), [KQ-2](key-questions/KQ-2-event-availability-payloads.md), [KQ-3](key-questions/KQ-3-delivery-semantics.md), [KQ-4](key-questions/KQ-4-blocked-state-permission.md), [KQ-5](key-questions/KQ-5-merge-semantics.md)
- Iterations: [plan 1](iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md)
- Reports: [synthesis](reports/2026-10-20-kimi-hook-observation-synthesis.md)
