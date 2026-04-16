## Why

System-skill installation currently persists Houmao install-state metadata inside each target tool home and uses that state as ownership proof before reinstalling a skill. That makes ordinary reinstall and development iteration more complicated than the project needs before 1.0, especially when the desired behavior is simply to refresh Houmao-owned skill content in the selected tool config home.

## What Changes

- **BREAKING**: Stop writing or reading `.houmao/system-skills/install-state.json` inside target tool homes for system-skill installation.
- Change `houmao-mgr system-skills install` so each selected current Houmao system-skill projection replaces the exact tool-native destination path when it already exists.
- Keep `--symlink` supported: symlink installs still remove any existing selected skill destination and create a directory symlink to the packaged asset root.
- Keep the destructive boundary narrow: only the selected current `houmao-*` skill projection paths are replaced; unrelated tool-home content and unselected skill directories are left alone.
- Change `system-skills status` semantics and documentation to describe filesystem discovery of current projected skills, not persisted install-state inspection.
- Remove old install-state compatibility, validation, and conflict-check requirements from the current contract.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-system-skill-installation`: replace install-state ownership and collision-failure behavior with stateless selected-skill overwrite projection.
- `houmao-mgr-system-skills-cli`: update install and status behavior so CLI results are based on selected projection and live filesystem discovery without install-state metadata.
- `docs-cli-reference`: update CLI reference requirements so user-facing docs describe stateless overwrite reinstall semantics and retained `--symlink` support.

## Impact

- Affected implementation: `src/houmao/agents/system_skills.py` and `src/houmao/srv_ctrl/commands/system_skills.py`.
- Affected tests: system-skill installer and CLI command tests that assert install-state files, unsupported legacy state failures, or non-owned collision rejection.
- Affected docs: `docs/reference/cli/system-skills.md`, `docs/reference/cli/houmao-mgr.md`, and any system-skill overview text that mentions install-state ownership.
- No new runtime dependency is required.
