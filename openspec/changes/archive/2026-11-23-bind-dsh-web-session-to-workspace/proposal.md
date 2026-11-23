# Proposal

## Why

Houmao starts DSH Web with the configured working directory, but the native browser can open a different Workspace and conversation. The operator needs to land on the session that receives Houmao prompts and mail notifications. [Issue #92](https://github.com/igamenovoer/houmao/issues/92)

## What Changes

- Register or reuse the native Workspace for the managed workdir and attach the exact managed session before marking the launch ready.
- Open that session through the existing gateway Web entry flow, including on a fresh browser before the first turn.
- Preserve Workspace membership on exact relaunch and attach each explicitly requested replacement to the same Workspace. Keep prior and unrelated sessions available as native history.
- Verify first entry, reload, relaunch, and notifier delivery in the maintained browser fixture.

## Capabilities

### New Capabilities

### Modified Capabilities

- `dsh-web-control` covers verified Workspace membership during managed lifecycle and exact session selection during browser entry.
- `test-agent-launch-fixtures` requires browser qualification of the runtime-managed Workspace and session.

## Impact

The DSH Web companion owns Workspace setup. The DSH Web backend supplies the verified browser target, and the existing gateway entry flow authorizes it. Qualification covers the maintained DSH Web fixtures and the operator reference documents the resulting handoff.
