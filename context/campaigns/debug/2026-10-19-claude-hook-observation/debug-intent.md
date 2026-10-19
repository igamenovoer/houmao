# Debug Intent: Claude Hook Observation

Date: 2026-10-19. Status: iteration 1 executed successfully on 2026-10-19 (ten paired captures incl. 2.1.296 floor repeat; gates G0-G3 passed; payload catalog and KQ-1..KQ-4 answers written; leftovers: P1.4 arm missing, P2.5 unreachable, Notification unsubscribed). Updated: 2026-10-19 — credential lane switched from `claude-openlux-0.5x` to `claude-deepseek` per user directive; iteration 1 closed same-day. Campaign directory: `context/campaigns/debug/2026-10-19-claude-hook-observation/`.

## Problem Statement

The OpenSpec change `add-cli-hook-observation-channel` was designed from the Claude Code hook documentation and from code-level analysis of Houmao's tracking stack, but no live hook traffic has ever been captured on this host. Every load-bearing assumption in the change is unverified: whether `--settings` is honored in TUI mode, which events fire at the supported floor and with what payloads, whether `prompt_id` correlation exists, what happens on Esc and on interactive permission denial, and how background work is reported over time. In parallel, the merge semantics in `design/state-transitions.md` (blocked phase, terminal latch, supersede, correction-after-staleness, the `work` axis) are rule designs without a single replay against real event streams.

The campaign question: before any production implementation, what is the appropriate way to parse and merge Claude hook events — and do the designed state-transition rules survive contact with real sessions?

## Relationship to the OpenSpec Change

This campaign is the pre-implementation evidence phase for `openspec/changes/add-cli-hook-observation-channel/`. It absorbs spike tasks 1.1 and 1.2 from that change's `tasks.md`. Findings amend the change's design/specs with dated corrections; they do not silently rewrite it. Production code under `src/` is not touched by this campaign.

## Starting Evidence

1. The change's design (`openspec/changes/add-cli-hook-observation-channel/design.md`, D1-D11) resolves collector topology, merge location, delivery, token channel, injection, event set, and enablement — all against documentation, none against live traffic.
2. `design/state-transitions.md` records the merged-state transition rules adopted during exploration (three-axis model with hook-only `blocked` and the session-scoped `work` axis, terminal latch with interrupt-only override, supersede-on-overlap, correction-after-staleness).
3. Installed Claude on this host is 2.1.303 (`claude --version`, 2026-10-19); the maintained floor is 2.1.296 (`src/houmao/agents/launch_policy/registry/claude.yaml:10`, `src/houmao/shared_tui_tracking/registry.py:126`). Primary captures run at 2.1.303; floor verification at 2.1.296 runs if a side-by-side install is practical.
4. The 2026-10-12 Claude TUI parsing campaign (`context/campaigns/debug/2026-10-12-claude-code-tui-parsing/`) established the paired-capture discipline, the two-boolean product contract, and the failure classes (false-ready, permission-wait blindness, silent-abort detection) that hooks should make authoritative.
5. The feature design docs (`context/features/2026-10-18-cli-hook-observation-channel/`) catalog the hook event model per official documentation; the session-work-axis feature (`context/features/2026-10-19-session-work-axis/`) defines the `work` axis whose clearing evidence this campaign must find.

## Comparison Arms

Implementation arms to be tried in `scripts/explore/claude-hook-observation/` (multiple variants per arm are expected; this campaign is explicitly iterative):

| Arm | Approach | What is evaluated |
| --- | --- | --- |
| E1 | Collector transport variants: HTTP collector vs command-hook file emitter vs hybrid | Delivery reliability, ordering, latency, failure behavior at floor and current versions |
| E2 | Normalizer and posture reducer variants against captured streams | Correlation correctness (prompt_id vs time-window), idempotency, orphan handling |
| E3 | Merge replay variants: projection-layer third authority vs unified-stream merge | Faithfulness to `design/state-transitions.md`, complexity, testability under virtual time |
| E4 | Work-axis clearing variants: terminal-payload mirror vs task-event-driven clearing (whichever events the spike discovers) | Whether `work=clear` can ever be said truthfully between turns |

## Capture Matrix (user requirement: at least 5 sessions)

Minimum seven scenario sessions, each producing a paired record (hook event stream + TUI pane recording + labels). Sessions S1-S7 are specified with frozen prompts and predeclared expectations in iteration 1.

| Session | Scenario | Must capture |
| --- | --- | --- |
| S1 | Normal multi-turn via short prompts | `SessionStart`, `UserPromptSubmit`, tool activity, `Stop`, session end |
| S2 | Direct pane input (typed, not gateway-submitted) | turn arming without gateway submission |
| S3 | Permission wait with allow and with deny (permissions enabled for this session only) | `PermissionRequest` timing vs modal paint, resolution evidence or its absence on deny |
| S4 | Manual compaction mid-session | `PreCompact`/`PostCompact` payloads, posture continuity across compaction |
| S5 | Background work: agent starts a background task and returns control | `Stop.background_tasks`, completion wake behavior, `idle_prompt` semantics, any task-lifecycle events |
| S6 | Esc interrupt mid-turn; best-effort API failure via relay cut | whether Esc emits `Stop`; `StopFailure` payload shape |
| S7 | Queued follow-up during a busy turn, then relaunch/resume | event ordering under queue consumption, new-generation isolation |

## Credential and Cost Lane (user directive 2026-10-19, supersedes the carried-over openlux lane)

All live LLM-driving sessions launch through `~/.local/bin/claude-deepseek`:

- Wraps the host claude binary (resolves to `~/.bun/bin/claude`, 2.1.303, verified 2026-10-19) with `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic` and `ANTHROPIC_AUTH_TOKEN` from `$DEEPSEEK_API_KEY` or `~/.local/bin/deepseek-api-key`; unsets `ANTHROPIC_API_KEY` and `CLAUDE_CODE_OAUTH_TOKEN`; passes `"$@"` through to claude.
- The launcher pins the model environment: `ANTHROPIC_MODEL=deepseek-flash[1m]` (the Sonnet alias maps to it), Opus alias `deepseek-v4-pro[1m]`, `CLAUDE_CODE_EFFORT_LEVEL=max`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW=786432`, `API_TIMEOUT_MS=600000`, autoupdater disabled. Campaign sessions pass **no `--model` argument**; the in-session bootstrap check verifies the model shows DeepSeek Flash. If the session shows anything else, the run stops before driving.
- The launcher always appends `--dangerously-skip-permissions`. Session S3 (permission capture) instead replicates the launcher environment directly (same endpoint, key read at runtime by the runner script, identical model pins) without the skip flag, so permission dialogs actually appear.
- The relay bills real money per token. Cost discipline: frozen short prompts per scenario, recordings reused across all analysis arms, no exploratory sessions beyond the plan.
- Credential hygiene: `deepseek-api-key`, tokens, and credential material are never read into chat, printed, copied, or embedded in artifacts. Raw hook payload quotes are limited to structure and field names, plus session-authored prompt text.

## Scope and Implementation Boundary

- In scope: live captures via tmux-driven Claude TUI sessions on this host; throwaway implementations in `scripts/explore/claude-hook-observation/`; replay and fault injection against captured streams; amendments to the OpenSpec change's planning artifacts with dated corrections.
- Read-only: production code under `src/`, the launcher script, credential files, and the 2026-10-12 campaign's frozen fixtures.
- Out of scope: production implementation (that is the OpenSpec apply phase, after this campaign resolves), Codex/Kimi hook support, `claude_headless` hook adoption.

## Success Criteria

- At least 5 scenario sessions (target 7) captured with paired hook + TUI streams and labels, covering the matrix above.
- The payload catalog for the v1 event set is confirmed or corrected per event, at 2.1.303 and (if installable) at the 2.1.296 floor.
- Every rule in `design/state-transitions.md` is either demonstrated against captured or fault-injected streams, or marked unresolved with the missing evidence named.
- The work-axis clearing question has a definite answer: which events (if any) clear `work` at the floor, or a confirmed payload-mirror fallback.
- Each E1-E4 arm ends with a chosen implementation variant and evidence for the choice, recorded in a campaign report.

## No-Product-Change Declaration

This campaign is diagnostic and experimental. It authorizes captures, throwaway code under `scripts/explore/claude-hook-observation/`, and dated amendments to the planning artifacts of `openspec/changes/add-cli-hook-observation-channel/`. It does not authorize changes to production code under `src/`, to existing tests, or to any launched provider's behavior.

## Links

- Key questions: [KQ-1](key-questions/KQ-1-settings-injection.md), [KQ-2](key-questions/KQ-2-delivery-semantics.md), [KQ-3](key-questions/KQ-3-payload-catalog.md), [KQ-4](key-questions/KQ-4-background-work.md), [KQ-5](key-questions/KQ-5-merge-semantics.md)
- Iterations: [plan 1](iterations/2026-10-19-plan-1-hook-capture-matrix.md)
