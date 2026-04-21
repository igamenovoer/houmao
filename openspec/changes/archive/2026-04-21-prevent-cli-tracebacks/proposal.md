## Why

`houmao-mgr` currently leaks raw Python exceptions for some ordinary operator-facing failure states, including uninitialized mailbox roots and malformed project recipe files. That makes expected recovery paths look like internal crashes, hides the maintained CLI contract behind traceback noise, and produces inconsistent guidance across sibling commands.

## What Changes

- Add a maintained `houmao-mgr` error-rendering contract so operator-facing command failures surface as normal CLI errors instead of Python tracebacks.
- Normalize the generic and project-scoped mailbox command families so expected mailbox bootstrap, missing-index, and unsupported-root failures return actionable CLI errors with the correct scope-specific recovery guidance.
- Normalize project-local recipe and role inspection flows so malformed preset files and related project-state read failures fail clearly without leaking internal exceptions.
- Add regression coverage for representative bad-state flows and audit maintained `houmao-mgr` command paths for the same raw-exception bug shape.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: strengthen the root `houmao-mgr` contract so maintained operator-facing failures do not escape as Python tracebacks.
- `houmao-mgr-mailbox-cli`: require mailbox-root inspection and maintenance failures to render as actionable CLI errors instead of raw exceptions.
- `houmao-mgr-project-mailbox-cli`: require project-scoped mailbox failures to render as actionable CLI errors with selected-overlay-aware recovery wording.
- `houmao-mgr-project-agents-presets`: require malformed preset-file and related recipe-read failures to surface as normal CLI errors.
- `houmao-mgr-project-agents-roles`: require role inspection flows that traverse preset references to surface malformed preset-file failures as normal CLI errors.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/main.py`, mailbox command/support modules, project command helpers, and project agent-definition command modules.
- Affected tests: `tests/unit/srv_ctrl/test_commands.py`, mailbox command tests, and project command tests for bad-state flows.
- Affected systems: operator-facing `houmao-mgr` CLI behavior and error wording across local and project-scoped workflows.
