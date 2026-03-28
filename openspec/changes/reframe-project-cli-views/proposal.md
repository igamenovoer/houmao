## Why

The current `houmao-mgr project` surface is pulling in two directions. Its low-level role and tool management commands do not mirror the actual `.houmao/agents/` source tree cleanly, while ordinary users still lack a simpler project-native UX for creating reusable specialists and working with a project-local mailbox. The exploration note at `context/logs/explore/20260328-172545-project-agents-cli-namespace-design.md` crystallized those gaps into one cohesive project-facing redesign.

Now is the right time to correct the shape because the existing project role/tool management work is still unstable, `project agent-roles` has not shipped, and the mailbox and specialist UX can be designed around one coherent project model instead of accreting more one-off subcommands.

## What Changes

- **BREAKING** Replace the documented `houmao-mgr project agent-tools ...` and planned `houmao-mgr project agent-roles ...` namespace with a filesystem-oriented `houmao-mgr project agents ...` tree.
- Add `houmao-mgr project agents roles ...` for project-local role scaffolding, inspection, preset management, and safe removal.
- Expand the existing project-local tool administration surface under `houmao-mgr project agents tools <tool> ...`, keeping tool auth CRUD and adding tool summary and setup-bundle management.
- Add `houmao-mgr project easy ...` as a higher-level project authoring view built around `specialist` and `instance` concepts that compile into the normal `.houmao/agents/` tree.
- Expand `houmao-mgr mailbox ...` so the generic mailbox-root CLI covers mailbox-account lifecycle and direct mailbox reads in addition to root bootstrap, status, repair, and cleanup.
- Add `houmao-mgr project mailbox ...` as a project-scoped wrapper over that same mailbox-root command family, automatically targeting the current project's `.houmao/mailbox/` root.
- Update project, native CLI, quickstart, and CLI reference docs to teach the new project views and stop documenting the old `project agent-tools` naming as the supported public surface.
- Supersede the direction captured in the active `add-project-role-and-tool-management-cli` change so the implementation target reflects the revised namespace and project UX model from the exploration note.

## Capabilities

### New Capabilities
- `houmao-mgr-project-agents-roles`: Project-scoped role management under `houmao-mgr project agents roles ...`, including role scaffolding and preset management.
- `houmao-mgr-project-easy-cli`: High-level specialist and instance project UX that compiles into the canonical `.houmao/agents/` source tree.
- `houmao-mgr-project-mailbox-cli`: Project-scoped mailbox commands that reuse the mailbox-root operations against the discovered `.houmao/mailbox/` root.

### Modified Capabilities
- `houmao-mgr-mailbox-cli`: The generic mailbox-root command family grows to cover mailbox-account lifecycle and direct mailbox reads.
- `houmao-mgr-project-cli`: The top-level `project` command family changes from `agent-tools` to `agents` and adds `easy` and `mailbox` subtrees.
- `houmao-mgr-project-agent-tools`: Project-local tool management moves under `project agents tools <tool> ...` while preserving the underlying tool auth and setup contracts.
- `houmao-srv-ctrl-native-cli`: The supported native `houmao-mgr project` tree changes to reflect `project agents ...`, `project easy ...`, and `project mailbox ...`.
- `docs-getting-started`: Getting-started docs change from raw role-file creation and `project agent-tools` examples to the revised project views.
- `docs-cli-reference`: CLI reference coverage changes to reflect the revised `houmao-mgr project` tree and nested project command families.

## Impact

- Affected code:
  - `src/houmao/srv_ctrl/commands/project.py`
  - project overlay helpers under `src/houmao/project/`
  - mailbox CLI reuse points under `src/houmao/srv_ctrl/commands/mailbox.py`
  - focused project and mailbox tests under `tests/unit/srv_ctrl/`
- Affected docs:
  - `docs/getting-started/quickstart.md`
  - `docs/getting-started/agent-definitions.md`
  - `docs/reference/cli/houmao-mgr.md`
  - mailbox-related workflow references that currently point only at top-level mailbox commands
- Affected OpenSpec artifacts:
  - this new change supersedes the direction in `openspec/changes/add-project-role-and-tool-management-cli/`
- Affected local filesystem surfaces:
  - `.houmao/agents/roles/...`
  - `.houmao/agents/tools/...`
  - `.houmao/agents/skills/...`
  - `.houmao/mailbox/`
  - project-owned `easy` metadata if introduced for specialist/instance reconstruction
