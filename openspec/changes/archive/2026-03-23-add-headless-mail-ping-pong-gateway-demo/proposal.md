## Why

Houmao now has the managed headless gateway primitives needed to demonstrate asynchronous agent-to-agent coordination through mailbox delivery and later gateway wake-up, but the repository still lacks a narrow, reproducible demo that shows those pieces working together as one conversation. A dedicated demo pack is needed now so users and maintainers can understand the intended turn model, thread continuity, and wake-up evidence without stitching together multiple unrelated tutorials.

## What Changes

- Add a new standalone demo pack under `scripts/demo/` that runs a two-agent mailbox ping-pong conversation through a demo-owned `houmao-server` and managed headless Claude Code and Codex agents.
- Reuse the tracked dummy-project fixture family and the tracked Claude/Codex `mailbox-demo-default` brain recipes, while adding thin demo-specific initiator and responder role packages that rely on the runtime-owned mailbox system skill.
- Define one explicit kickoff and thread-key contract, bounded `wait` polling and timeout behavior, and a five-round conversation success rule of ten sent messages and eleven completed turns.
- Keep all Houmao-generated files for the demo under `<demo-home>/outputs/`, including runtime roots, mailbox roots, the shared registry, jobs roots, copied projects, server state, and stable demo-owned inspection and report artifacts.
- Keep v1 regression coverage pytest-based and explicitly defer a pack-local live-agent `autotest/` harness to a later change if the pack contract stabilizes.

## Capabilities

### New Capabilities
- `mail-ping-pong-gateway-demo-pack`: A standalone tutorial/demo pack for a two-agent mailbox conversation that progresses through later gateway wake-ups, reuses the tracked mailbox-demo fixture family, and keeps all demo-owned generated state under `outputs/`.

### Modified Capabilities

## Impact

- New demo-pack assets under `scripts/demo/` and a backing module under `src/houmao/demo/`
- New demo-specific role packages and fixture wiring under `tests/fixtures/agents/`
- Managed-agent and gateway client/orchestration usage through `/houmao/agents/*`
- New inspection and report artifact contracts plus pytest-based automated demo-pack coverage
- New documentation for the operator workflow, kickoff/thread contract, timeout posture, and `outputs/` ownership model
