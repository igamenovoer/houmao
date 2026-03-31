## Why

The current demo splits Claude and Codex runs into separate output subdirectories, which makes the manual operator flow heavier than it needs to be. Follow-up commands such as `attach`, `watch-gateway`, `send`, and `notifier ...` often require `--demo-output-dir`, and every fresh run rebuilds overlay-backed specialist state that could be reused safely.

## What Changes

- Simplify `scripts/demo/single-agent-mail-wakeup/` to use one canonical `outputs/` state root instead of `outputs/<tool>/`.
- Change follow-up commands to resolve the active run from the canonical persisted state so operators do not need to pass `--demo-output-dir` during normal stepwise use.
- Preserve reusable overlay-backed project-easy specialist state across runs so operators do not recreate or reimport specialists and auth content every time they restart the demo.
- Reset only run-local state on a new `start`, including copied project content, mailbox state, runtime state, logs, deliveries, and evidence.
- Adjust the documented and supported `matrix` behavior so it no longer depends on concurrent per-tool output roots.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `single-agent-mail-wakeup-demo`: simplify the output-root contract to a single canonical `outputs/` root, preserve reusable overlay specialist state across runs, and remove the need for normal follow-up commands to target tool-specific output directories.

## Impact

- Affected code: `src/houmao/demo/single_agent_mail_wakeup/`, `scripts/demo/single-agent-mail-wakeup/`, focused unit tests, and the demo README.
- Affected behavior: stepwise operator commands, start/reprovision semantics, persisted demo-state discovery, and matrix execution semantics.
- Affected systems: demo-owned project overlay reuse, project-easy specialist lifecycle, demo mailbox reset behavior, and follow-up command ergonomics.
