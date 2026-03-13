# Runtime Module Naming

## Approved Name

The canonical runtime module path is `gig_agents.agents.realm_controller`, and the canonical short name in docs is `realm_controller`.

## Why This Name

This module owns more than launch-time setup. It manages interactive lifecycle, resumed control flows, gateway attachment, mailbox operations, and tmux/CAO session state. `realm_controller` better matches that controller role than `brain_launch_runtime`.

## Required Surfaces

Update the following surfaces together whenever the public runtime name changes:

- source tree: `src/gig_agents/agents/realm_controller/`
- module invocation examples: `python -m gig_agents.agents.realm_controller`
- runtime reference page: `docs/reference/realm_controller.md`
- `send-keys` reference page: `docs/reference/realm_controller_send_keys.md`
- runtime test trees: `tests/unit/agents/realm_controller/` and `tests/integration/agents/realm_controller/`

## Explicit Non-Goals

Do not use this naming change to rename:

- runtime subcommands such as `build-brain`, `start-session`, `send-prompt`, or `mail`
- runtime env vars or `AGENTSYS_*` identities
- internal class/function names unless a module-path edit requires it
