# gig-agents

`gig-agents` is the canonical runtime home for agent brain building, session launch/resume control, and CAO server launcher workflows.

This repository owns the runtime modules that were extracted from `agent-system-dissect`:

- `gig_agents.agents.brain_builder`
- `gig_agents.agents.brain_launch_runtime`
- `gig_agents.cao`

## Runtime Ownership

For new runtime development, this repository is canonical. The source workspace keeps a copy-first compatibility mirror during migration.

## Install

```bash
pixi install
pixi shell
```

Or install as a package:

```bash
pip install -e .
```

## CLI Entry Points

- `gig-agents-cli` for brain/runtime workflows
- `gig-cao-server` for local `cao-server` start/status/stop

Examples:

```bash
gig-agents-cli --help
gig-cao-server --help
```

## Agent Definition Directory Contract

Runtime command surfaces resolve agent definitions with precedence:

1. CLI `--agent-def-dir`
2. env `AGENTSYS_AGENT_DEF_DIR`
3. default `<pwd>/.agentsys/agents`

`--agent-def-dir` points to the directory containing `brains/`, `roles/`, and `blueprints/`.

## CAO Prerequisite

CAO is an external prerequisite and is not declared as a Python dependency of `gig-agents`.

Install CAO separately and ensure required executables are on `PATH`:

```bash
uv tool install cli-agent-orchestrator
command -v cao-server
command -v tmux
```

## Development Checks

```bash
pixi run format
pixi run lint
pixi run typecheck
pixi run test-runtime
```
