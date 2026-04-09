## Why

`houmao-mgr` currently treats credential management as a deep leaf under `project agents tools <tool> auth ...`, which makes credentials look like projection-tree maintenance instead of a first-class operator concern. That shape also leaves plain agent-definition directories without any supported credential-management surface even though build and launch code can consume credentials from those trees.

## What Changes

- Add a first-class `houmao-mgr credentials ...` command family dedicated to credential management.
- Add an explicit `houmao-mgr project credentials ...` wrapper for project-scoped credential management in the active overlay.
- Add support for managing credentials in plain agent-definition directories through `credentials ... --agent-def-dir <path>`.
- **BREAKING** Remove the maintained credential CRUD surface from `houmao-mgr project agents tools <tool> auth ...` and move that ownership to the new credential interface.
- Keep project-overlay credentials catalog-backed with display-name semantics and opaque bundle refs.
- Define direct agent-definition-directory credential management as filesystem-backed operations over `tools/<tool>/auth/<name>/`, including explicit rename behavior for that backend.
- Update packaged credential-management skills and CLI/docs routing to point to the new command families.

## Capabilities

### New Capabilities
- `houmao-mgr-credentials-cli`: Manage Claude, Codex, and Gemini credentials through a dedicated CLI family that can target either the active project overlay or an explicit agent-definition directory.

### Modified Capabilities
- `houmao-srv-ctrl-native-cli`: Add the top-level `credentials` command family to the supported `houmao-mgr` tree.
- `houmao-mgr-project-cli`: Add `project credentials` as an explicit project view for credential management.
- `houmao-mgr-project-agent-tools`: Remove auth CRUD from the tool-maintenance subtree and keep that subtree focused on tool inspection and setup bundles.
- `houmao-manage-credentials-skill`: Route the packaged credential-management skill through `credentials ...` / `project credentials ...` instead of `project agents tools <tool> auth ...`.
- `docs-cli-reference`: Document the new `credentials` and `project credentials` families as first-class CLI surfaces.
- `docs-system-skills-overview-guide`: Update canonical credential-management routing in the narrative system-skills guide.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/main.py`, `src/houmao/srv_ctrl/commands/project.py`, new or refactored credential-command helpers under `src/houmao/srv_ctrl/commands/`, and packaged skill assets under `src/houmao/agents/assets/system_skills/`.
- Affected artifacts: command help surfaces, credential-management skill guidance, and CLI/getting-started documentation.
- Affected workflows: project-local credential CRUD, credential management for plain agent-definition directories, and any operator or agent guidance that currently routes through `project agents tools <tool> auth ...`.
