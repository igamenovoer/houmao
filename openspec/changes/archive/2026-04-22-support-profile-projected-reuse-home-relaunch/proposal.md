## Why

Current `--reuse-home` behavior is specified as a fresh launch that happens to rebuild onto a compatible preserved home. That does not match the operator intent for profile-backed restart workflows, where the agent is already down, the old tmux session is gone, the launch profile has been updated, and the operator wants to restart the same logical agent on the same home with the new projection applied.

The resulting mismatch makes `--reuse-home` feel like a low-level preserved-home selector instead of the higher-level "restart this stopped agent with my updated profile" workflow operators expect. We need one explicit contract that treats preserved-home restart as continuity of the same logical managed agent without requiring prior registry cleanup.

## What Changes

- Redefine `--reuse-home` for managed local launch as a stopped-agent restart workflow rather than a merely fresh launch against a compatible preserved home.
- Require the prior agent instance to already be down and its tmux session absent before `--reuse-home` restart proceeds; `--reuse-home` remains distinct from live-owner takeover.
- Make profile-backed `--reuse-home` restart project the current stored launch profile onto the preserved managed home, overwriting the same Houmao-managed projection targets while leaving untouched non-projected files in place.
- Define preserved-home compatibility around the same logical managed identity, same runtime root, and the same CLI tool type; specialist-backed or profile-backed settings may change between the prior run and the restart.
- Keep stopped lifecycle metadata as the continuity anchor so a stopped preserved-home restart does not require separate manual registry cleanup before launch.
- Restore the prior tmux session name by default for reused-home restart when the stopped record still carries one and the operator does not provide a stronger explicit `--session-name` override.
- Keep direct CLI launch overrides and explicit `--session-name` override semantics stronger than stored launch-profile defaults during reused-home restart.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-agents-launch`: change `--reuse-home` from preserved-home fresh launch semantics to stopped-agent restart semantics with current-input reprojection and default prior tmux-session-name reuse.
- `houmao-mgr-project-easy-cli`: change easy-instance `--reuse-home` to the same stopped-agent restart contract, especially for easy-profile-backed launch after profile edits.
- `brain-launch-runtime`: change reused-home runtime behavior so restart consumes stopped lifecycle continuity, reapplies current launch inputs onto the preserved home, and prefers the prior tmux session name when restarting the same logical agent.

## Impact

- Affected CLI behavior in `src/houmao/srv_ctrl/commands/agents/core.py` and `src/houmao/srv_ctrl/commands/project_easy.py`.
- Affected runtime and session-identity behavior in `src/houmao/agents/realm_controller/runtime.py`, related registry resolution, and launch-path predecessor-home handling.
- Affected tests around reused-home launch, stopped-record restart, and tmux session-name continuity.
- Affected specs for `houmao-mgr-agents-launch`, `houmao-mgr-project-easy-cli`, and `brain-launch-runtime`.
