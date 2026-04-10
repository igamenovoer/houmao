## Why

Stopping a local tmux-backed managed agent after its tmux session has already disappeared can currently leak a Python traceback from `houmao-mgr` instead of showing operator-facing CLI error text. That makes an ordinary stale-session condition look like an internal crash and forces operators to read implementation details instead of a clear recovery message.

## What Changes

- Extend the native `houmao-mgr` error boundary so expected runtime and managed-agent resolution failures render as normal CLI error output rather than Python tracebacks.
- Normalize local managed-agent resume/control failures caused by stale tmux-backed session state into managed-agent contextual CLI errors.
- Define the stale local `agents stop` path so it preserves non-zero exit behavior while reporting a sensible error message that explains the target is no longer live.
- Add regression coverage for stale tmux-backed managed-agent stop/control failures so traceback leaks do not recur.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: extend native managed-agent control error handling so stale tmux-backed local targets fail with explicit CLI error text instead of leaking Python tracebacks.

## Impact

- Affected CLI: `houmao-mgr agents stop` and other local managed-agent command paths that resume a local runtime controller from shared-registry metadata.
- Affected code: native CLI top-level error handling, local managed-agent target resolution/resume helpers, and the stale tmux-backed resume path used by tmux-backed runtimes.
- Affected tests: native CLI and managed-agent resolution regression tests for runtime error wrapping.
- No public API additions are required.
