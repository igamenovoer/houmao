## Why

`houmao-mgr agents cleanup session|logs|mailbox` can abort when a stopped managed-session envelope is already partial, especially when `manifest.json` or other session-local artifacts have been deleted first. Operators invoke cleanup precisely after interrupted teardown, stale pointers, or manual recovery work, so the cleanup path needs to stay best-effort and remove whatever still exists instead of failing on missing files.

## What Changes

- Make managed-session cleanup resolve a runtime-owned session root even when the manifest pointer is stale or missing, as long as the target can still be recovered safely from an explicit path or fresh shared-registry record.
- Make `agents cleanup session|logs|mailbox` skip missing or manifest-dependent artifacts instead of raising when the remaining cleanup work can still proceed safely.
- Preserve live-session safety by continuing to block destructive cleanup when local manifest or shared-registry evidence still shows the target session as live.
- Add regression coverage for missing-manifest, stale-registry-pointer, and already-absent-artifact cleanup paths.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `houmao-mgr-cleanup-cli`: Require managed-session cleanup commands to treat missing manifests and missing session-local artifacts as non-fatal, continue manifest-independent cleanup from the resolved session root, and preserve live-session blocking when local evidence still shows the session as active.

## Impact

- Managed-session cleanup resolution and artifact deletion flow in `src/houmao/srv_ctrl/commands/runtime_cleanup.py`.
- Cleanup command error handling in `src/houmao/srv_ctrl/commands/agents/cleanup.py`.
- Shared-registry-assisted cleanup resolution where `runtime.session_root` can outlive a stale manifest pointer.
- Regression coverage in `tests/unit/srv_ctrl/test_cleanup_commands.py` and adjacent cleanup-related unit suites.
