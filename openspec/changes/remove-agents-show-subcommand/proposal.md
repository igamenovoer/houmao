## Why

`houmao-mgr agents show` adds a second managed-agent inspection command without providing essential operator value beyond the supported `agents state`, `agents gateway ...`, and `agents turn ...` surfaces. Keeping the extra subcommand expands the CLI surface, documentation burden, and test matrix for a detail-oriented view that is no longer needed as a first-class operator command.

## What Changes

- **BREAKING** Remove the native `houmao-mgr agents show` subcommand from the supported `agents` command family.
- Update operator-facing help, reference docs, and workflow guidance to stop advertising `agents show` and to point callers to `agents state`, `agents gateway tui ...`, or other existing inspection commands as appropriate.
- Remove or update CLI tests and workflow fixtures that currently expect `agents show` to exist.
- Preserve the underlying managed-agent detail API and internal detail payload helpers unless another surface still needs to change them separately.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `houmao-srv-ctrl-native-cli`: the supported native `agents` command family no longer includes the `show` subcommand or related operator guidance.

## Impact

- Affected CLI code under `src/houmao/srv_ctrl/commands/agents/`.
- Affected CLI documentation and workflow guides that reference `houmao-mgr agents show`.
- Affected CLI shape tests and any demos or fixtures that assert the `show` subcommand exists.
