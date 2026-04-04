## Why

`make-operations-project-aware` established the shared overlay-selection and local-root contract, but the maintained `houmao-mgr project ...` surface still has a second layer of behavior embedded directly in `project.py`. Many subcommands still call `_require_project_overlay()` instead of routing through the shared resolver, so operators still see inconsistent "run `project init` first" behavior across roles, presets, tool bundles, auth bundles, and easy specialist or instance commands.

The remaining work is not another root-layout redesign. It is a focused audit that decides which `project` subcommands should bootstrap a missing overlay, which ones must remain non-creating, and how missing-overlay errors should be surfaced consistently for maintained project-local flows.

## What Changes

- Modify maintained `houmao-mgr project agents ...` tool, setup, auth, role, and preset subcommands so they use the shared project-aware resolver instead of direct `_require_project_overlay()` gating.
- Define two command classes for maintained project-local flows:
  - bootstrap-on-write flows that can sensibly create the active overlay before writing new project-local state
  - non-creating inspection or existing-state flows that must resolve selection state without bootstrapping a missing overlay
- Clarify missing-overlay behavior for maintained `houmao-mgr project easy specialist ...` and `project easy instance ...` commands so create and launch continue to ensure the overlay, while inspection and stop or remove paths stay non-creating and fail clearly when no project overlay exists.
- Refresh operator-facing help, error, and payload expectations for these project command families so the overlay-selection contract matches the maintained command behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-cli`: Change maintained `project` subcommand behavior so project-local create or materialize flows bootstrap through the shared resolver, while read-only or existing-state project flows remain non-creating and report missing overlays consistently.
- `houmao-mgr-project-easy-cli`: Change maintained easy specialist and instance inspection or removal flows to use the shared resolver in non-creating mode, while preserving ensure-on-create and ensure-on-launch behavior for specialist creation and instance launch.

## Impact

- Affected code is centered in [src/houmao/srv_ctrl/commands/project.py](/data1/huangzhe/code/houmao/src/houmao/srv_ctrl/commands/project.py) and the shared overlay-resolution helpers it already imports.
- Affected specs are the `houmao-mgr-project-cli` and `houmao-mgr-project-easy-cli` capability contracts.
- Affected tests are the project CLI and project easy command suites that currently exercise missing-overlay, bootstrap, and project-owned runtime selection behavior.
