## Why

The repository already demonstrates single-agent gateway wake-up, interactive CAO TUI driving, and headless mailbox ping-pong, but it does not yet show the specific workflow of one live TUI agent being awakened by filesystem-backed email, processing one nominated unread message, acknowledging the work in chat, and marking the message read through the gateway mailbox facade. A dedicated demo pack is needed now so maintainers can observe and explain that turn model directly for both Claude Code and Codex without stitching together multiple unrelated tutorials.

## What Changes

- Add a new standalone demo pack under `scripts/demo/` for a single mailbox-enabled TUI session that is awakened by gateway unread-mail polling.
- Support the same demo contract for `claude` and `codex`, with the operator selecting the tool per run instead of launching both tools concurrently in one workflow.
- Reuse the tracked copied dummy-project and lightweight `mailbox-demo` fixture family, while adding a thin demo-specific role or blueprint layer only if needed to keep the agent focused on the bounded mail-read and chat-ack task.
- Add a harness-driven three-turn workflow that injects one new email every five seconds only when the mailbox has no unread mail, waits for the agent to process it, and then repeats until three processed messages have been observed.
- Add inspect and verification artifacts that explain gateway notifier behavior, mailbox unread-state transitions, the three injected messages, and human-review TUI evidence without snapshotting exact model wording.
- Keep all demo-owned generated state under one selected output root so runtime, mailbox, gateway, copied project, and verification artifacts remain isolated and easy to inspect.

## Capabilities

### New Capabilities
- `tui-mail-gateway-demo-pack`: A standalone demo pack for a single CAO-backed TUI agent that is awakened by filesystem mailbox unread mail through a live gateway and completes a bounded three-turn mail-processing loop.

### Modified Capabilities

## Impact

- New demo-pack assets under `scripts/demo/`
- New backing module under `src/houmao/demo/`
- New or adjusted tracked demo fixture wiring under `tests/fixtures/agents/`
- New regression coverage for the demo-pack contract under `tests/unit/demo/` and, if warranted, `tests/integration/demo/`
- Reuse of existing runtime CLI, gateway mailbox facade, filesystem mailbox transport, and interactive CAO inspection patterns
