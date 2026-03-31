## Why

Project-aware Houmao flows currently assume the default overlay root `<cwd>/.houmao` and nearest-ancestor `.houmao/houmao-config.toml` discovery are the only ways to locate project-local Houmao state. That is awkward for CI and controlled automation because the effective overlay directory cannot be redirected through the environment, so ambient lookup and `houmao-mgr project` subcommands bind to whichever checkout-local `.houmao/` happens to exist.

## What Changes

- Add `HOUMAO_PROJECT_OVERLAY_DIR` as an absolute-path environment override for the project overlay directory used by project-aware Houmao resolution.
- Make `houmao-mgr project init` and `houmao-mgr project status` honor `HOUMAO_PROJECT_OVERLAY_DIR` before default `<cwd>/.houmao` or nearest-ancestor `.houmao/houmao-config.toml` discovery.
- Make `houmao-mgr project` subcommands that require the active overlay resolve it from `HOUMAO_PROJECT_OVERLAY_DIR` before falling back to current-directory ancestor discovery.
- Make project-aware build and launch resolution use `HOUMAO_PROJECT_OVERLAY_DIR` before nearest-ancestor project discovery when no explicit `--agent-def-dir` or `AGENTSYS_AGENT_DEF_DIR` override is present.
- Make `houmao-mgr project mailbox ...` resolve the project mailbox root from the env-selected overlay directory when `HOUMAO_PROJECT_OVERLAY_DIR` is set.
- Update operator and reference docs to describe the new precedence contract and CI-oriented usage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-cli`: project bootstrap, status, and project-aware path resolution now honor `HOUMAO_PROJECT_OVERLAY_DIR` before default or ancestor overlay discovery.
- `houmao-mgr-project-mailbox-cli`: project mailbox commands resolve the project mailbox root from `HOUMAO_PROJECT_OVERLAY_DIR` when present.
- `brain-launch-runtime`: deprecated compatibility entrypoints and ambient project-aware agent-definition lookup add `HOUMAO_PROJECT_OVERLAY_DIR` into precedence.
- `docs-cli-reference`: CLI docs must describe the new `HOUMAO_PROJECT_OVERLAY_DIR` precedence contract.
- `docs-getting-started`: onboarding docs must describe `.houmao/` as the default overlay under `<cwd>` and explain the direct overlay-dir env override for CI.

## Impact

- Affected code: project overlay discovery helpers, `houmao-mgr project` commands, project mailbox wrapper commands, and ambient build/launch resolution helpers.
- Affected behavior: CI and automation can select the effective overlay directory directly without relying on `cwd` or pre-existing checkout-local discovery.
- Affected docs/tests: project CLI, runtime resolution, and getting-started docs plus unit coverage for env-selected overlay directories.
