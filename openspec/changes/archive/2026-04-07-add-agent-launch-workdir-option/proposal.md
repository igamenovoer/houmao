## Why

Houmao currently ties managed-agent launch cwd to the invocation cwd, and for some launch paths that same value also drives project-overlay and agent-definition resolution. That prevents operators from launching an agent against one source Houmao project while intentionally running the agent inside a different repository or subdirectory.

## What Changes

- Add an explicit `--workdir <path>` runtime-cwd override to `houmao-mgr agents launch`.
- Add an explicit `--workdir <path>` runtime-cwd override to `houmao-mgr project easy instance launch`.
- Rename the existing `houmao-mgr agents join --working-directory` flag to `--workdir` for CLI consistency.
- Update launch resolution so a launch that originates from a Houmao project keeps using that source project overlay, agent-definition tree, runtime root, jobs root, and mailbox root even when `--workdir` points somewhere else.
- Keep `agents relaunch` on the persisted manifest workdir rather than introducing a new relaunch-time cwd override.
- Update CLI reference and operator-facing docs to explain the distinction between source project context and runtime workdir.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `houmao-mgr-agents-launch`: add `--workdir` and separate source-project resolution from runtime workdir for managed launch.
- `houmao-mgr-agents-join`: rename the current cwd override flag from `--working-directory` to `--workdir`.
- `houmao-mgr-project-easy-cli`: add `--workdir` to easy instance launch without letting that override change the selected project overlay or specialist source.
- `docs-cli-reference`: document the new `--workdir` contract and the source-project-versus-runtime-workdir distinction.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/agents/native_launch_resolver.py`, and any shared launch helpers that currently derive source context from `working_directory`.
- Affected behavior: local managed launch, easy instance launch, join help/CLI shape, launch result output, and relaunch expectations based on the persisted manifest cwd.
- Affected docs/tests: CLI reference pages, getting-started/easy-launch guidance, and focused unit/integration coverage for launch resolution and join option parsing.
