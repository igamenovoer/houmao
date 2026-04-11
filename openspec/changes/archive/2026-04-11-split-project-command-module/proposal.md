## Why

`src/houmao/srv_ctrl/commands/project.py` has grown to roughly 5,000 lines and now mixes unrelated project command families, shared project overlay helpers, launch-profile storage logic, mailbox wrappers, easy specialist workflows, and leftover credential helper code in one module. This makes local changes slower and riskier because contributors must reason about a broad command surface and a large helper namespace before making focused project CLI updates.

## What Changes

- Split the current `project.py` implementation into focused project command modules while preserving the public `houmao-mgr project ...` CLI surface.
- Keep `houmao.srv_ctrl.commands.project` as the stable public command entrypoint that exports `project_group` during the refactor.
- Move project command families and helper logic into smaller modules organized by concern, such as project common helpers, tool setup commands, role/preset commands, launch-profile commands, easy workflow commands, and project mailbox commands.
- Remove or relocate project-local helper code that has been superseded by existing dedicated modules, after confirming it has no runtime callers.
- Add regression coverage that proves help shape and focused project-command behavior are unchanged after the module split.
- No breaking command-line behavior is intended.

## Capabilities

### New Capabilities

- `project-command-module-layout`: Architectural requirements for keeping the `houmao-mgr project` command implementation decomposed into focused modules while preserving the stable public import and CLI behavior.

### Modified Capabilities

- None. This change is intended as a behavioral no-op refactor of the command implementation structure.

## Impact

- Affected code:
  - `src/houmao/srv_ctrl/commands/project.py`
  - New sibling modules under `src/houmao/srv_ctrl/commands/` for extracted project command families and shared helpers
  - Project command tests under `tests/unit/srv_ctrl/test_project_commands.py`
  - CLI shape tests if they assert project command help structure
- Public CLI behavior should remain unchanged for `houmao-mgr project init`, `status`, `credentials`, `agents`, `easy`, and `mailbox`.
- No new runtime dependencies are expected.
