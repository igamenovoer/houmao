# Hermes Runtime Qualification

The self-hosted fixture case used the installed `hermes` command from PATH and the fixture's loopback OpenAI Chat Completions peer. Each lane used a separate Hermes home and workspace. Ink ran on an isolated tmux server. The peer verified the synthetic credential, selected model, and the role and skill text present in provider requests. The fixture README describes how to reproduce these lanes.

| Surface | Mode | Observed Evidence |
| --- | --- | --- |
| Raw | Service | Stock ACP initialized, opened a conversation, and completed two prompts in it. |
| Raw | Headless | Two finite clients completed turns in the same native conversation. |
| Raw | TUI | Ink reached its ready screen and displayed the deterministic peer response after a terminal prompt. |
| Managed | Service | Two prompts completed on one ACP connection. Exact relaunch opened a new ACP connection, loaded the saved native ID, and completed a third prompt. Managed stop closed the service. |
| Managed | Headless | Two different worker PIDs used the same native ID. The peer received the first turn as context and preserved the second prompt's newline and shell metacharacters. Exact relaunch completed a third prompt. Managed stop succeeded. |
| Managed | TUI | Houmao published an Ink pane and negotiated structured session state, submission, receipts, and replay. Human input won a race after the idle check. Hermes issued separate human and managed admission IDs. The managed admission entered the native queue and settled with its own assistant output. |

## Lifecycle and Delivery

- A stale TUI exact-session selector refused before changing the live daemon or the saved native conversation.
- An independently started daemon for the same managed home was adopted and stopped. Exact TUI relaunch preserved the native conversation and workspace through a fresh daemon incarnation.
- After the selected daemon exited during an Ink attachment, the stock client started a replacement for the same home. Houmao observed the new daemon and the original queued managed admission. The lost human turn remained unresolved and managed readiness stayed closed.
- Closing the isolated Ink pane during a managed turn changed the terminal attachment to `detached`. Native inspection stayed available and the original admission completed.
- The Houmao gateway restarted during a managed Ink turn. Its PID changed while the Hermes daemon, logical session, and native admission IDs stayed fixed. The durable request reached `completed`, and the peer saw exactly one provider request for the prompt.
- A manager interrupt during a delayed ACP request returned the selected operation's native `interrupted` result. A delayed headless turn completed after the prelaunch authorization window closed.
- An operator post triggered the offline notifier. The durable request captured a verified `queued` receipt. The notifier suppressed overlap while the work was pending and admitted another periodic reminder after settlement. The original mail peek returned the same read and placement state.
- Stock headless JSONL exposed native session and turn-result evidence. The client kept its native admission ID internal, so an interrupt without an attributable admission was refused. The adapter preserves uncertainty when a finite client exits without matched settlement.

## Automated Verification

- The Pixi runtime suite passed 2,413 tests with isolated test tmux servers.
- The focused Hermes, manager, passive-server, AG-UI, and CCCC regression run passed 236 tests.
- Ruff lint, strict mypy, the strict MkDocs build, and strict OpenSpec validation passed.

## Unexercised Provider Lanes

Cloud API credentials were outside this run. CCCC delivery was exercised in the unit suite. The live communication check used the offline mailbox.
