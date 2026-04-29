## 1. Regression Coverage

- [x] 1.1 Add registry-level regression coverage showing normal publish still rejects replacing a fresh healthy active generation.
- [x] 1.2 Add managed-agent stop coverage for a stale active local tmux-backed record with readable relaunch authority, asserting the same generation transitions to `stopped` without ownership conflict.
- [x] 1.3 Add managed-agent stop coverage for a degraded active local tmux-backed record, asserting the broken tmux session is cleaned up and the same generation transitions to `stopped`.
- [x] 1.4 Add managed-agent stop coverage for stale/degraded records with unreadable manifest or agent-definition authority, asserting the record is retired or removed and the result explains fresh launch is required.
- [x] 1.5 Add managed-agent relaunch coverage for stale/degraded active records, asserting recovery first clears active ownership and then publishes a new active generation for the same `agent_id`.
- [x] 1.6 Add relaunch failure coverage showing that if stopped-session revival fails after stale-active recovery, the registry remains stopped/relaunchable rather than stale active.
- [x] 1.7 Add stop error-output coverage for unexpected registry transition failure, asserting no traceback and an exact `agents cleanup session ... --purge-registry --dry-run` guidance command.

## 2. Broken Active Lifecycle Recovery

- [x] 2.1 Introduce a native managed-agent helper that re-reads the target registry record, checks the expected generation, and re-probes local tmux authority before broken-active mutation.
- [x] 2.2 Implement stale/degraded active-to-stopped transition that preserves the existing generation, runtime relaunch locators, terminal last-session metadata, and mailbox metadata while clearing active liveness and gateway state.
- [x] 2.3 Implement unrelaunchable broken-active retirement/removal using existing registry cleanup semantics when manifest or agent-definition authority is unreadable.
- [x] 2.4 Ensure degraded recovery tears down only the recorded Houmao-owned tmux session before lifecycle transition.
- [x] 2.5 Keep normal shared-registry publish behavior strict for healthy active records and avoid adding a broad force overwrite path.

## 3. Stop and Relaunch Integration

- [x] 3.1 Update `stop_managed_agent` stale/degraded local paths to use the common broken-active recovery helper instead of publishing a stopped record through a new stopped-revival generation.
- [x] 3.2 Update `relaunch_managed_agent` stale/degraded local paths to transition verified broken active records to stopped before invoking stopped-session revival.
- [x] 3.3 Preserve existing stopped-record relaunch behavior for records that are already in lifecycle state `stopped`.
- [x] 3.4 Ensure relaunch rollback behavior leaves recoverable stopped continuity when revival fails after broken-active transition.

## 4. Stop Failure Guidance

- [x] 4.1 Add a stop-specific guidance formatter that records known `agent_name`, `agent_id`, `manifest_path`, `session_root`, tmux session name, completed phase, and failed phase.
- [x] 4.2 Emit exact follow-up commands for cleanup dry-run, cleanup execution, retry, or relaunch recovery using the most precise available selector.
- [x] 4.3 Ensure destructive guidance suggests `--dry-run` first unless destructive recovery was already explicitly requested.
- [x] 4.4 Ensure guidance never recommends killing tmux sessions based only on friendly-name or `HOUMAO-` prefix matching.

## 5. Verification

- [x] 5.1 Run `pixi run test tests/unit/srv_ctrl/test_managed_agents.py tests/unit/agents/realm_controller/test_registry_storage.py`.
- [x] 5.2 Run `pixi run test tests/unit/srv_ctrl/test_cleanup_commands.py` if cleanup guidance or lifecycle retirement behavior changes.
- [x] 5.3 Run `pixi run test`.
- [x] 5.4 Run `pixi run lint` and `pixi run typecheck`.
