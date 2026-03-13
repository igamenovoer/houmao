## Why

The reference material for runtime-managed agents and the agent gateway is currently spread across broad overview pages, OpenSpec changes, source modules, and tests. That makes it hard for first-time users to form a correct mental model of how sessions, direct control, queued gateway control, mailbox flows, and persisted runtime state fit together, while developers and maintainers still have to reconstruct exact interface contracts from code when debugging or extending the system.

We need dedicated reference homes now because the runtime-managed agent model and the gateway sidecar have grown into stable enough subsystems to deserve source-aligned documentation under `docs/reference/agents/` and `docs/reference/gateway/`. The docs also need to teach as well as specify: readers should get intuitive framing first, but still be able to find exact protocols, error-handling rules, message-passing behavior, and state-management details without hunting across the repo.

## What Changes

- Add a dedicated `docs/reference/agents/` reference subtree for runtime-managed agents, including session lifecycle, interaction paths, public interfaces, message-passing modes, state management, and runtime error or recovery behavior.
- Add a dedicated `docs/reference/gateway/` reference subtree for the agent gateway, including attachability versus live bindings, strict attach and status contracts, HTTP routes, durable queue or state artifacts, lifecycle handling, and reconciliation or recovery behavior.
- Establish a documentation writing pattern for both subtrees that starts with mental models and intuitive framing, then drills into exact technical detail, representative artifacts, examples, and source references.
- Require important multi-component procedures in these docs to include embedded Mermaid sequence diagrams when the interaction flow materially helps understanding.
- Update docs navigation and broader runtime reference pages so readers can discover the new agent and gateway subtrees without relying on source-directory spelunking.
- Keep the new docs explicitly grounded in current implemented behavior and tests, making clear what is runtime-owned and supported in v1 versus what remains deferred or future-facing.

## Capabilities

### New Capabilities

- `agents-reference-docs`: Structured reference documentation for runtime-managed agents under `docs/reference/agents/`, including information architecture, required coverage for public interfaces and interaction paths, and internal runtime architecture guidance.
- `agent-gateway-reference-docs`: Structured reference documentation for the agent gateway under `docs/reference/gateway/`, including required coverage for attach contracts, live HTTP surfaces, durable state artifacts, queue semantics, lifecycle handling, and recovery behavior.

### Modified Capabilities

## Impact

This change is expected to affect `docs/reference/`, docs navigation pages, and the documentation workflow for future runtime or gateway changes. Likely touched files include `docs/reference/index.md`, `docs/reference/brain_launch_runtime.md`, `docs/reference/agents_brains.md`, and new pages under `docs/reference/agents/` and `docs/reference/gateway/`. The documented source surfaces will primarily come from `src/gig_agents/agents/brain_launch_runtime/cli.py`, `src/gig_agents/agents/brain_launch_runtime/runtime.py`, `src/gig_agents/agents/brain_launch_runtime/gateway_models.py`, `src/gig_agents/agents/brain_launch_runtime/gateway_storage.py`, `src/gig_agents/agents/brain_launch_runtime/gateway_service.py`, related error models, and gateway-focused tests. This change should not alter runtime behavior by itself, but it will create a stable documentation contract so future runtime and gateway work can update these references incrementally instead of growing a few broad overview pages indefinitely.
