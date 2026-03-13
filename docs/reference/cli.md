# CLI And Environments

`Houmao` uses a standalone Pixi manifest in this repository.

## Install

```bash
pixi install
```

## Primary Commands

- Runtime CLI: `houmao-cli`
- CAO launcher CLI: `houmao-cao-server`

Runtime subcommands:

- `build-brain`
- `start-session`
- `send-prompt`
- `send-keys`
- `mail`
- `stop-session`

Module equivalents:

```bash
pixi run python -m houmao.agents.realm_controller --help
pixi run python -m houmao.cao.tools.cao_server_launcher --help
```

## Common Runtime Flags

Useful `start-session` overrides:

- `--cao-base-url http://localhost:<port>` or `http://127.0.0.1:<port>` for a supported launcher-managed loopback CAO endpoint
- `--mailbox-transport filesystem`
- `--mailbox-root <path>`
- `--mailbox-principal-id <principal-id>`
- `--mailbox-address <full-address>`

The runtime `mail` command operates on resumed mailbox-enabled sessions and supports `check`, `send`, and `reply`.

Command reminders:

- `mail send` recipients must use full mailbox addresses such as `AGENTSYS-orchestrator@agents.localhost`.
- `mail send` and `mail reply` require body content via `--body-file` or `--body-content`.
- `send-keys` is the low-level CAO control-input surface; use `send-prompt` or `mail` for higher-level runtime-owned turns.

For the dedicated mailbox quickstart, contracts, and operational guidance, see [Mailbox Reference](mailbox/index.md).

## Agent Definition Directory

Runtime commands use two agent-definition-directory resolution models:

1. Build/start and manifest-path control: `--agent-def-dir`, then `AGENTSYS_AGENT_DEF_DIR`, then `<pwd>/.agentsys/agents`.
2. Name-based tmux-backed `send-prompt`, `send-keys`, `mail`, and `stop-session`: explicit `--agent-def-dir` override first, otherwise the addressed session's published `AGENTSYS_AGENT_DEF_DIR`.

## Pixi Tasks

```bash
pixi run format
pixi run lint
pixi run typecheck
pixi run test-runtime
pixi run build-dist
pixi run check-dist
```
