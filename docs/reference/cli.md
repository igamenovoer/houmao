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

Runtime commands resolve agent definitions with precedence:

1. `--agent-def-dir`
2. `AGENTSYS_AGENT_DEF_DIR`
3. `<pwd>/.agentsys/agents`

## Pixi Tasks

```bash
pixi run format
pixi run lint
pixi run typecheck
pixi run test-runtime
pixi run build-dist
pixi run check-dist
```
