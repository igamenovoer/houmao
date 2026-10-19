# CLI Hook Observation Channel Feature Requirement

## Goal

Give Houmao a second, structured observation channel for managed CLI agents by collecting provider-native lifecycle hooks and merging them with TUI parsing. The channel must make state tracking more robust by providing authoritative facts for turn start, turn end, terminal failure, permission waits, context maintenance, subagent activity, and background work, while leaving surface facts such as readiness, draft input, and queued input with the TUI tracker.

The first provider adapter is Claude Code. The observation model, merge rules, diagnostics, fallback behavior, and qualification model must remain provider-neutral so later adapters can reuse them.

## Non-Goals

- It does not replace TUI parsing. Hooks and TUI parsing are complementary channels with explicit authority boundaries.
- It does not support arbitrary user-authored hooks or third-party hook plugins as observation inputs.
- It does not add hook support to joined sessions or unmanaged provider launches in the first release.
- It does not guarantee state when a provider, an organization policy, or a client mode disables hooks.
- It does not treat hooks as a security boundary against a malicious agent. They are observations, not attestations.
- It does not change provider behavior. Observer hooks must remain silent, non-blocking, and decision-free.
- It does not cover every provider event. It selects the events that materially improve state correctness.
- It does not define a new GUI or AG-UI surface, though it may enrich existing state payloads additively.
- It does not automatically repair, restart, or prompt an agent based on hook observations.

## Users And Workflows

- **Houmao operator**: Launches a managed Claude agent, inspects `state`, gateway state, or passive-server state, and sees whether the hook channel is active, degraded, or unavailable. The operator does not configure hooks manually.
- **Managed agent**: Runs unchanged. The provider emits hooks because the managed launch installed an observer configuration. The agent receives no additional prompts or context from the observer channel.
- **Gateway and passive server**: Consume merged state for observation and prompt admission. They use hook lifecycle facts to avoid false-ready admission and to report terminal failures earlier and more accurately.
- **Houmao maintainer**: Adds or revises provider adapters, version gates, event mappings, and merge rules.
- **Qualification engineer**: Captures TUI recordings and hook event streams, replays them together, injects faults, and produces evidence that the merged tracker matches labeled behavior.
- **Diagnostician**: Inspects hook channel health, raw event logs, and conflict diagnostics when state looks wrong.

## Functional Requirements

- The system must inject a session-scoped observer hook configuration into managed Claude Code launches without modifying operator-authored settings.
- The system must collect hook events into a durable, append-only, session-scoped store.
- The system must normalize provider hook payloads into a provider-neutral observation model with session, prompt, tool, and subagent correlation identifiers.
- The system must merge hook observations with TUI detector output and lifecycle pipeline output using explicit authority rules.
- The merge path must use the existing RxPY dependency and treat hook observations as an observable source in the same resolution stream as TUI and lifecycle observations.
- The system must publish hook channel health and conflict diagnostics on local inspection surfaces.
- The system must fall back to TUI-only behavior when the hook channel is unavailable, stale, disabled by policy, or not trusted for the workspace.
- The system must correlate gateway-submitted prompts with hook turn-start events and avoid double-arming a turn.
- The system must support session start, resume, relaunch, stop, and cleanup without leaving stale hook configuration or collector processes.
- The system must keep raw hook payloads local, restrict file permissions, and exclude secrets and raw tool inputs from public state payloads.
- The system must version-gate provider events and tolerate unknown, malformed, duplicate, and out-of-order events.
- The system must preserve TUI-only behavior and existing public state semantics when hooks are absent.
- The system must expose enough evidence to qualify the merged tracker against recorded TUI sessions and live provider turns.

## System Boundaries

- In scope: managed Claude Code launches through `local_interactive` and, where practical, `claude_headless`; hook configuration injection; local event collection; event normalization; merge with `TuiTrackerSession` and `LiveSessionTracker`; diagnostics; fallback; cleanup; qualification tooling and replay evidence.
- Out of scope: joined sessions, unmanaged launches, Codex and Kimi adapters in the first release, provider hook authoring by users, GUI work, security attestation, automatic lifecycle remediation, and changes to provider internals.

## Operational Constraints

- Observer hooks must never block, deny, modify, or accelerate provider actions. Command hooks must exit 0, write nothing to stdout, and never return exit code 2.
- The hook path must stay off the provider hot path where possible. Boundary events may be synchronous; high-frequency tool events should be asynchronous or cheap.
- The collector must acknowledge events within the configured timeout and must not make the provider wait on disk or downstream processing.
- `SessionStart` and `Setup` cannot use Claude HTTP hooks; they need a command-hook path.
- `SessionEnd` has a short default budget and must not be used as a cleanup dependency.
- Interactive Claude Code withholds hooks until the workspace is trusted. Managed unattended launches must pre-seed trust, and the channel must diagnose an untrusted workspace.
- Hook availability depends on provider version, organization policy, client mode, and settings precedence. The channel must detect absence and degrade rather than fail the session.
- The raw event store may contain prompts, paths, tool inputs, and other sensitive material. It must be local, permission-restricted, excluded from registry records, and cleaned with the session.
- The merged tracker must not regress the TUI-only qualification gate when hook events are absent.
- The design must remain compatible with the current `TrackedStateSnapshot`, `HoumaoTrackedDiagnostics`, gateway status, and passive-server state surfaces through additive optional fields.

## Assumptions

- Claude Code 2.1.296 or later exposes the core hook events needed by this feature, with possible per-event differences above the floor.
- A managed launch can install a session-scoped observer through `--settings` or through a managed-home `settings.json` merge.
- Unattended launches already trust the resolved working directory, so interactive hooks are not withheld.
- Hook payloads are JSON objects delivered on stdin for command hooks and in the request body for HTTP hooks.
- `prompt_id` is available often enough to correlate turn start and terminal events; when absent, time-window correlation is a bounded fallback.
- The TUI tracker remains installed, qualified, and authoritative for readiness, draft input, pending input, modal rendering, and interrupt inference.
- The existing tracker's Rx streams can accept an additional observable source without changing TUI-only semantics.
- The gateway or another local process can read the session-scoped event store while the managed session is live.
- Provider hook schemas may evolve. Unknown events and unknown payload fields must be tolerated rather than rejected.

## Open Questions

- Which exact Claude event set is safe to require at 2.1.296, and which events need capability probing or version gates?
- Is the default transport an HTTP collector, a command emitter writing to a file, or a hybrid with both?
- Should the channel be enabled by default for managed Claude launches, or introduced behind an opt-in flag or launch-profile field?
- Should hook-derived final assistant text become part of the public managed-agent state, or stay local to turn evidence?
- Should `claude_headless` adopt hooks in the first release, or continue to rely on `stream-json` until the TUI path is qualified?
- How should joined sessions expose that hooks are unavailable without confusing the operator?
- What retention and redaction policy should apply to raw hook payloads and conflict diagnostics?
- Should the observation channel ever influence provider behavior, such as asking for a retry after `StopFailure`, or remain strictly observational?
