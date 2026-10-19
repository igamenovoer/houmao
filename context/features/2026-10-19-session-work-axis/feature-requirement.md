# Session Work Axis Feature Requirement

## Goal

Introduce a session-scoped `work` axis as fundamental tracked state so that managed-agent state can represent "the turn ended, the surface is prompt-ready, and provider-acknowledged work is still running". Every existing implementation that treats prompt-ready as task-terminal must be inventoried and adjusted to account for the split. The axis must remain provider-neutral, additive to the public contract, and honest about evidence gaps: sessions without hook evidence report `work=unknown` rather than a guessed `clear`.

## Non-Goals

- It does not change turn lifecycle semantics. A turn still ends at the provider's terminal event or TUI-settled equivalent; `last_turn.result=success` remains truthful about the turn.
- It does not gate prompt admission by default. Prompting while `work=pending` is legitimate queued or parallel work; stricter policies are a later, opt-in decision.
- It does not make TUI parsing responsible for background-work detection in v1. TUI corroboration is allowed only if the provider renders a reliable indicator.
- It does not auto-remediate: no restarts, nudges, or prompts are triggered by `work` state.
- It does not redefine `settled` consumers' existing behavior without an explicit per-consumer adjustment decision.

## Users And Workflows

- **Houmao operator**: Inspects agent state and can distinguish "idle and done" from "idle with background work outstanding" instead of assuming they are the same.
- **Orchestrator (agent loops, gateway automation)**: Gates the next task assignment on `settled` rather than prompt-ready alone, so a new task is not piled onto an agent that still has outstanding background work.
- **Gateway and passive server**: Project the `work` axis through existing state surfaces additively, without changing admission defaults.
- **Houmao maintainer**: Extends the tracked-state vocabulary, wires hook evidence into the axis, and keeps TUI-only behavior byte-equivalent for sessions without hook evidence.
- **Qualification engineer**: Records sessions with background work, labels `work` expectations, and replays them against the merged tracker.

## Functional Requirements

- The tracked state model SHALL expose a session-scoped `work` axis with the vocabulary `pending | clear | unknown`, additive and optional on all public surfaces.
- The system SHALL derive `settled = (turn.phase == ready) AND (work == clear)` as an explicit state fact, since prompt-ready alone no longer carries that meaning.
- With hook evidence available, terminal events that report background work SHALL set `work=pending`, and the system SHALL clear the axis from live provider completion evidence when the provider exposes such events at the supported floor (conditional promotion, decided by spike evidence).
- When the provider exposes no completion events at the floor, the axis SHALL mirror the most recent terminal event's payload, and this staleness window SHALL be documented as a known limit with a revisit trigger.
- Sessions without hook evidence, degraded channels, and providers without background-work reporting SHALL report `work=unknown`; TUI-only sessions SHALL keep byte-equivalent existing state.
- The system SHALL treat the axis as orthogonal to `turn.phase`: `blocked`, `interrupted`, and maintenance states may all coexist with `work=pending`.
- Existing implementations that consume tracked state SHALL be inventoried for the prompt-ready-equals-done assumption, and each SHALL be adjusted or explicitly recorded as intentionally unchanged.
- Qualification assets SHALL gain at least one recorded scenario where the agent backgrounds work and returns control, with labeled `work` expectations.

## System Boundaries

- In scope: the tracked-state model and its public projections, hook-sourced evidence wiring (with the CLI Hook Observation Channel), consumer inventory and adjustment, qualification coverage, and documentation of the new semantics.
- Out of scope: provider behavior changes, automatic remediation, new admission policies enabled by default, GUI surfaces, and TUI-only background-work inference in v1.

## Operational Constraints

- The axis is additive: consumers that ignore it must behave exactly as today, and TUI-only qualification replays must pass unchanged.
- `work=unknown` must never be presented as `clear`; absence of evidence is not evidence of completion.
- The axis must not regress admission responsiveness: admission decisions in this release read the same fields they read today.
- Evidence sourcing must stay provider-neutral in the state model even though the first adapter is Claude Code.

## Assumptions

- Claude Code reports outstanding background work in terminal-event payloads (`Stop.background_tasks`, `session_crons`) at the 2.1.296 floor.
- Whether task-lifecycle hooks or notifications at the floor track background shell work is unknown and assigned to the hook channel spike (task 1.2); the axis semantics tolerate either outcome.
- Orchestrators currently key "assign next task" decisions on prompt-ready plus settled turn outcomes; they can adopt `settled` without protocol changes.
- A background-task completion may wake an idle agent into a new turn; spike evidence will determine whether turn tracking needs a wake-up rule.

## Open Questions

- Which provider events clear `work` at the floor, and what are their payloads? (Spike 1.2.)
- Does background completion produce a provider-initiated turn, and does `UserPromptSubmit` fire for it?
- Should `settled` be computed by the tracker and published, or computed by consumers from `turn.phase` and `work`?
- Final public naming: `work.posture` versus a flat tristate field.
- Which consumers get adjusted in v1 versus recorded as intentionally unchanged?
- Does a future admission policy that requires `settled` belong in the gateway or in orchestrator policy?
