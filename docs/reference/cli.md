# CLI And Environments

`gig-agents` uses a standalone Pixi manifest in this repository.

## Install

```bash
pixi install
```

## Primary Commands

- Runtime CLI: `gig-agents-cli`
- CAO launcher CLI: `gig-cao-server`

Module equivalents:

```bash
pixi run python -m gig_agents.agents.brain_launch_runtime --help
pixi run python -m gig_agents.cao.tools.cao_server_launcher --help
```

## Agent Definition Directory

Runtime commands use two agent-definition-directory resolution models:

1. Build/start and manifest-path control: `--agent-def-dir`, then `AGENTSYS_AGENT_DEF_DIR`, then `<pwd>/.agentsys/agents`.
2. Name-based tmux-backed `send-prompt`, `send-keys`, and `stop-session`: explicit `--agent-def-dir` override first, otherwise the addressed session's published `AGENTSYS_AGENT_DEF_DIR`.

## Pixi Tasks

```bash
pixi run format
pixi run lint
pixi run typecheck
pixi run test-runtime
pixi run build-dist
pixi run check-dist
```
