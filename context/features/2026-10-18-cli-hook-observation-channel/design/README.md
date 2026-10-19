# Design

This directory contains module, interface, and contract design notes for the CLI Hook Observation Channel.

## Index

| Design Doc | Purpose | Status |
| --- | --- | --- |
| [Public Interfaces](public-interfaces.md) | Provider-neutral observation model, channel lifecycle, merge contract, public diagnostics, errors, persistence, and security | Draft |
| [Claude Hook Adapter](claude-hook-adapter.md) | Claude Code event matrix, observer configuration, collector transport, event mapping, version gates, and launch integration points | Draft |
| [Qualification and Rollout](qualification-and-rollout.md) | Test layers, scenario matrix, evidence contracts, gates, fallback validation, and staged enablement | Draft |

## Module Map

- **Hook adapter**: provider-specific event catalog, payload parsing, version gates, and observer configuration generation.
- **Hook collector**: local authenticated intake for provider events, receive-order stamping, and append-only persistence.
- **Observation normalizer**: converts provider payloads into provider-neutral observations with session, prompt, tool, and subagent correlation.
- **Channel health monitor**: tracks active, unavailable, stale, disabled, untrusted, and error states.
- **Rx merge pipeline**: combines hook observations, TUI snapshots, and lifecycle observations in one reactive stream using explicit authority rules.
- **Public state projection**: adds additive observation-channel and conflict diagnostics to local, gateway, and passive-server state surfaces.
- **Admission adapter**: applies merged lifecycle facts to `ready_only`, `if_no_pending`, and `always` prompt admission.
- **Qualification harness**: records hook events alongside TUI snapshots, replays merged evidence, injects faults, and checks TUI-only equivalence.

## Design Principles

- **Two channels, separate facts.** Hooks own provider lifecycle facts. TUI parsing owns surface facts. Neither channel is allowed to silently impersonate the other.
- **One reactive resolution path.** Hook observations, TUI snapshots, lifecycle observations, and timer events are reduced by the same Rx stream. Producers do not resolve state.
- **Observer only.** The hook channel must never alter provider behavior. Hooks exit zero, emit no stdout, and make no decisions.
- **Absence is not evidence.** A missing hook event never proves that a turn did not start, did not end, or did not fail.
- **Fail open for the agent, fail closed for admission.** A broken hook channel must not break the managed session. Conditional prompt admission must remain closed when activity or pending input is unresolved.
- **Additive public contracts.** Existing snapshots and routes keep their meaning. New fields are optional and versioned.
- **Raw evidence stays local.** Public surfaces expose event names, counts, error classes, and conflict reasons, not prompts, tool inputs, or secrets.

## Open Questions

- Which design decisions need ADRs before implementation: enablement policy or public final-text exposure?
- Should the merged Rx stream live inside `LiveSessionTracker` or a separate composed session beside it?
- Should the channel be part of the existing session manifest or a sibling runtime artifact?
- Which provider-neutral observation vocabulary should be stable, and which fields should remain adapter-private?
- How should the stream handle late TUI snapshots after a hook terminal event?
