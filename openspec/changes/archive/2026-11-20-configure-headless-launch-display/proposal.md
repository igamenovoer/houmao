# Proposal

## Why

Project launches fix headless pane output at `plain` and `concise`, so operators cannot select detailed live output through the supported launch workflow. Issue #87 requests reusable profile defaults and one-shot overrides for the renderer controls Houmao already supports. [Issue #87](https://github.com/igamenovoer/houmao/issues/87)

## What Changes

- Add `--headless-display-style` and `--headless-display-detail` to `houmao-mgr project agents launch` and specialist-backed `project profile create` and `set`.
- Persist optional profile values in launch posture. Give each field its own `--clear-*` option on `project profile set`.
- Resolve each field independently from the launch flag, saved profile value, or built-in default. Validate that configured display settings apply to the resolved headless mode before runtime preparation.
- Pass the effective settings into the session manifest and live tmux renderer. Use the recorded settings when relaunching the instance.
- Document how operators configure the display, check the stored values, and read provider-emitted detail in a headless pane.

## Capabilities

### New Capabilities

### Modified Capabilities

- `houmao-mgr-project-easy-cli` adds reusable display defaults, one-shot launch flags, and mode preflight.
- `headless-output-rendering` specifies how project launch settings reach the live pane and persist across relaunch.
- `docs-cli-reference` documents the supported configuration workflow and display behavior.

## Impact

The change affects the public project commands, profile posture storage and projection, launch validation on the execution owner, session manifest and bridge verification, and the launch documentation. The supported profile path uses a specialist-backed project profile, and one-shot flags also work for direct specialist launches.
