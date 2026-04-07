## Why

Operators currently cannot ask `houmao-mgr` to report its own packaged version through the standard CLI surface. That makes stale-install diagnosis harder than it needs to be, especially when a globally installed `houmao-mgr` behaves differently from the current workspace checkout.

## What Changes

- Add a root `--version` option to `houmao-mgr`.
- Make `houmao-mgr --version` print the packaged Houmao version and exit successfully without requiring a subcommand.
- Update the CLI reference for `houmao-mgr` so the root synopsis and option coverage include `--version`.
- Add test coverage for the new root version-reporting behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: extend the root `houmao-mgr` command contract to expose `--version`
- `docs-cli-reference`: document the `houmao-mgr` root `--version` option in the CLI reference

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/main.py`, existing package version helpers under `src/houmao/version.py`, and root CLI tests
- Affected docs: `docs/reference/cli/houmao-mgr.md`
- User-facing CLI surface: `houmao-mgr --version`
