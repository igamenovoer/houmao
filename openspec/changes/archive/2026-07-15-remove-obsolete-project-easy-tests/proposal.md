## Why

The public `houmao-mgr project easy` command was retired, but maintained tests still include obsolete names, patch targets, and one mocked assertion that treats the removed command as valid. This creates false confidence because the mocked test passes while the real CLI rejects the same command.

## What Changes

- Remove tests whose only contract is an obsolete `project easy ...` command shape.
- Rename retained specialist, profile, and project-agent tests so they describe the supported flat `project specialist`, `project profile`, and `project agents` surfaces.
- Avoid treating the legacy internal `project_easy` module name as a public command contract; retain implementation-targeted monkeypatches only where isolation requires them.
- Preserve the negative CLI-shape assertion that `project easy` is absent and preserve behavioral coverage for the promoted commands.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-easy-cli`: Require maintained tests to validate the retired prefix only as an absent command and to exercise supported behavior through the promoted project command paths.

## Impact

- Unit tests under `tests/unit/srv_ctrl/` and `tests/unit/demo/`.
- CLI-shape integration tests under `tests/integration/srv_ctrl/`.
- No public CLI, runtime, persisted data, or compatibility behavior changes.
