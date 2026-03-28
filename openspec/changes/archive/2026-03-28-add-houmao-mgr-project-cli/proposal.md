## Why

`houmao-mgr` currently assumes operators will hand-create or copy an agent-definition tree and then manually wire local auth bundles into it. That is awkward in an arbitrary working repository, especially when the intended posture is a local-only Houmao overlay rather than a tracked repo-owned integration.

We need a first-class project-local workflow that lets an operator stand up Houmao state in one command, keep that state entirely under `.houmao/`, and add tool-specific local credentials without inventing ad hoc directory conventions by hand.

## What Changes

- Add a new top-level `houmao-mgr project` command family for local project bootstrap and inspection.
- Add `houmao-mgr project init` to create a repo-local `.houmao/` tree, write `.houmao/houmao-config.toml`, create `.houmao/.gitignore` that ignores all generated local state, and seed the local `agents/` source root used by Houmao project workflows.
- Add project discovery rules that locate the nearest ancestor `.houmao/houmao-config.toml` and use that project-local config as the default source of truth for project-aware path resolution.
- Add `houmao-mgr project credential ...` commands that author tool-specific local auth bundles under `.houmao/agents/tools/<tool>/auth/<name>/` rather than creating a separate credential registry format.
- Update build/launch onboarding documentation to use the new local project-init workflow instead of telling operators to manually copy or construct `.agentsys/agents`.

## Capabilities

### New Capabilities
- `houmao-mgr-project-cli`: Repo-local Houmao project discovery, `.houmao` bootstrap, local project config, and project-scoped credential authoring commands.

### Modified Capabilities
- `houmao-srv-ctrl-native-cli`: The native `houmao-mgr` tree gains a top-level `project` command family.
- `docs-getting-started`: Getting-started guidance changes from manual `.agentsys/agents` setup to the supported `houmao-mgr project init` local overlay workflow.

## Impact

- Affected code:
  - `src/houmao/srv_ctrl/commands/main.py`
  - new `src/houmao/srv_ctrl/commands/project.py`
  - agent-definition root resolution helpers used by build and launch flows
  - project-local config and bundled project-template assets
- Affected systems:
  - repo-local `.houmao/` project overlays
  - project-local agent-definition trees under `.houmao/agents/`
  - local auth-bundle authoring for Claude, Codex, and later tools
- Affected docs:
  - `docs/reference/cli/houmao-mgr.md`
  - getting-started quickstart and agent-definition setup docs
