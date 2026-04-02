## Why

Project-aware Houmao commands currently discover the nearest ancestor `.houmao/houmao-config.toml` by default. That works well for repo-wide behavior, but it prevents operators from opting into strictly local `<cwd>/.houmao` scoping when they want a subdirectory to behave as an independent Houmao project root without using an explicit overlay-dir override.

## What Changes

- Add one environment variable that controls project-overlay discovery mode for project-aware commands.
- Keep the default discovery behavior as nearest-ancestor search bounded by the current Git worktree, preserving the existing repo-oriented default.
- Add a cwd-only discovery mode that skips ancestor overlay discovery and only treats `<cwd>/.houmao` as the ambient project-overlay candidate when no explicit overlay-dir override is supplied.
- Update project-aware status and operator-facing wording so the selected discovery mode is reflected clearly.
- Document the new discovery-mode env and its interaction with `HOUMAO_PROJECT_OVERLAY_DIR`, ambient overlay discovery, and default `<cwd>/.houmao` bootstrap behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-cli`: project-aware overlay discovery gains an env-controlled mode that can disable nearest-ancestor discovery and restrict ambient lookup to `<cwd>/.houmao`.
- `docs-cli-reference`: CLI reference documents the new project-overlay discovery-mode env and the updated ambient resolution contract.
- `docs-getting-started`: onboarding docs explain the default nearest-ancestor behavior and the opt-in cwd-only discovery mode.

## Impact

- Affected code: `src/houmao/project/overlay.py` and project-aware command surfaces that report overlay-selection details.
- Affected tests: project overlay resolution tests and CLI shape/wording tests for project-aware status and launch flows.
- Affected docs: project-aware operations reference, CLI reference, and getting-started guidance that describe overlay discovery precedence.
