## Why

The current `houmao-mgr` CLI duplicates project-scoped workflows at the top level to expose explicit target selection, most visibly in `houmao-mgr credentials --project`, even though the same behavior already exists under `houmao-mgr project credentials`. This makes the command tree harder to explain and creates pressure for every project subcommand to grow a parallel top-level wrapper.

Houmao now treats direct native-agent material as an internal compatibility layer, so project target selection should live on the project command family itself while direct native-agent and brain-building plumbing should live under `internals`.

## What Changes

- Add a group-level `houmao-mgr project --project-dir <dir> ...` selector that targets a human-facing project directory and resolves its `.houmao/` overlay.
- Keep omitted `--project-dir` behavior as automatic project discovery from the current working directory.
- Preserve `houmao-mgr project init` as the explicit project creation/validation command, with `--project-dir <dir>` creating or validating `<dir>/.houmao`.
- **BREAKING**: Remove the maintained top-level `houmao-mgr credentials ...` project-target wrapper behavior from the public CLI shape; project credentials are managed through `houmao-mgr project [--project-dir <dir>] credentials ...`.
- Move direct plain native-agent credential CRUD, if retained, under `houmao-mgr internals native-agent credentials ...` rather than keeping it as a top-level target variant.
- **BREAKING**: Move `houmao-mgr brains build` out of the top-level public manager surface and into an internal native-agent/build surface such as `houmao-mgr internals native-agent brain build`.
- Update command-template/config-draft/system-skill/docs guidance so agents route ordinary project work to `project --project-dir` and direct provider-aligned file-tree work to `internals native-agent`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-cli`: Add group-level project directory selection and make it the only maintained explicit project-targeting mechanism for project subcommands.
- `houmao-mgr-credentials-cli`: Remove the public top-level target-variant credentials family and route project credentials through `project credentials`; define any retained direct native-agent credential CRUD as internal.
- `houmao-mgr-native-agent-internals-cli`: Add retained direct native-agent credential and brain-build plumbing to the internal native-agent surface.
- `brain-launch-runtime`: Move the direct brain build CLI entrypoint under internals while preserving the build behavior used by launch pipelines.
- `docs-cli-reference`: Update the documented `houmao-mgr` shape, command examples, and credential/brain routing.
- `houmao-manage-credentials-skill`: Update packaged credential-management guidance to use `project --project-dir ... credentials` for project credentials and internals-only routing for direct native-agent credentials.
- `houmao-manage-agent-definition-skill`: Update packaged agent-definition guidance to avoid top-level target-variant commands and route direct native-agent/build work through `internals native-agent`.
- `houmao-mgr-command-template-renderer`: Update maintained template ids and rendered argv to reflect `project --project-dir`, removed top-level credentials templates, and new internal native-agent paths.

## Impact

- CLI command registration and help text in `src/houmao/srv_ctrl/commands/main.py`, `project.py`, `credentials.py`, `brains.py`, and `internals.py`.
- Project overlay resolution helpers in `src/houmao/project/overlay.py` and project command helpers in `src/houmao/srv_ctrl/commands/project_common.py`.
- Existing tests for project overlay selection, project credentials, direct credential backends, brain build commands, command templates, and system skills.
- CLI docs and packaged system skills that currently mention `houmao-mgr credentials`, `--project`, `--agent-def-dir`, or top-level `brains build`.
- This is intentionally breaking for unstable development: update callers and docs to the new command tree rather than adding long-lived compatibility shims.
