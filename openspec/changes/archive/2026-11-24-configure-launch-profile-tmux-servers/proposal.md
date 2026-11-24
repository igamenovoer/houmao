# Proposal

## Why

Project launches currently derive their tmux server from the execution scope or shell environment. Profiles need to express where agents should run, and the fixture launcher needs a shared Houmao server by default while retaining a way to exercise multiple servers.

## What Changes

- Add four tmux server choices to project launch profiles and one-shot project launches. `user-default` selects the execution account’s native default, `new` starts a private server for the new instance, `socket` connects to an existing server at an absolute path, and `houmao-default` selects Houmao’s shared server for that execution owner.
- Store the Houmao default socket in the shared registry and start its server on demand. Persist the resolved socket in the runtime manifest for later operations and relaunches.
- Resolve a one-shot selection before the stored profile selection, then use the existing launch selection when both are omitted. An admitted executor’s server binding constrains the result.
- **BREAKING** `scripts/agents/test-fixtures/fixture.py` uses `houmao-default` for local tmux-backed runs. Use `--tmux-server new` to prepare an isolated run for cross-server tests or debugging.

## Capabilities

### New Capabilities

- `houmao-default-tmux-server` defines the owner’s shared registry record, first-use startup, and recovery at the recorded socket.

### Modified Capabilities

- `agent-launch-profiles` adds a typed tmux server selection to both project launch-profile authoring lanes, inspection, and projection.
- `houmao-mgr-agents-launch` defines one-shot selection, precedence, and validation before force takeover.
- `tmux-integration-runtime` defines startup permissions for each selection and preserves the resolved binding across lifecycle operations.
- `test-agent-launch-fixtures` makes the Houmao server the local fixture default and keeps cross-server qualification explicit.

## Impact

This affects the project catalog and profile commands, managed launch preflight, the shared libtmux adapter and runtime manifests, shared registry storage, and fixture preparation and lifecycle. Operator documentation and isolated integration coverage will describe both shared and private launches.
