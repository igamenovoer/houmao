## Why

The future operator-facing boundary is the Houmao pair: `houmao-srv-ctrl` plus `houmao-server`. This change therefore no longer targets raw runtime gateway lifecycle around `houmao-cli` or raw `cao_rest`. Pair-managed TUI sessions already persist `backend = "houmao_server_rest"` so callers can treat the pair as the public authority and ignore child-CAO details, but gateway attach still behaves like a runtime-side concern instead of a pair-owned command.

That leaves two practical gaps for the pair UX:

- `houmao-srv-ctrl` has no native `agent-gateway` command even though pair-managed sessions already expose managed-agent gateway routes through `houmao-server`;
- delegated pair launches do not yet publish stable gateway attachability pointers early enough for a "run this from inside the agent tmux session" workflow; and
- the current gateway topology still assumes a detached out-of-band process, which blocks a useful operator mode where the gateway is visible in another tmux window while one stable agent surface remains reserved.

The intended pair behavior is stricter than the earlier draft scope: `houmao-srv-ctrl` should behave as if raw `cao-server` / `cao_rest` are not part of the public control model, even under the explicit `cao` subgroup. The pair CLI should manage pair-owned `houmao_server_rest` sessions and let the server remain the public authority.

## What Changes

- Add a pair-owned `houmao-srv-ctrl agent-gateway` lifecycle surface for pair-managed `houmao_server_rest` sessions instead of relying on raw runtime CLI entrypoints.
- Support two attach modes for `houmao-srv-ctrl agent-gateway attach`: explicit target mode with `--agent`, and current-session mode without `--agent` that infers the target from tmux-published Houmao gateway env, treats the persisted `houmao_server_rest` attach contract as authoritative for `api_base_url` plus `session_name`, and fails closed when those envs are missing, stale, or identify a non-pair session.
- Route pair CLI attach through `houmao-server` managed-agent gateway lifecycle rather than through raw local `cao_rest` or `houmao-cli` attach behavior.
- Allow pair-managed `houmao_server_rest` sessions to host the gateway sidecar in an auxiliary tmux window in the same managed agent session while keeping tmux window `0` reserved for the agent surface, keeping the `houmao-server` process itself outside that tmux session, and persisting one runtime-owned same-session gateway execution handle for detach and cleanup.
- Seed stable gateway capability and tmux env pointers during pair launch or launch registration through the existing runtime-owned gateway publication seam, so current-session attach becomes valid only after both publication and matching managed-agent registration are complete.
- Preserve or restore window `0` across gateway attach, detach, crash cleanup, and same-session agent relaunch while keeping non-zero windows intentionally non-contractual.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: change the gateway lifecycle contract so the public attach surface for pair-managed TUI sessions is `houmao-srv-ctrl agent-gateway`, scoped to `houmao_server_rest`, with explicit-target and current-session attach modes, authoritative current-session routing from the persisted attach contract, and same-session auxiliary-window support for the gateway sidecar.
- `brain-launch-runtime`: change pair-managed `houmao_server_rest` launch and runtime tmux topology so window `0` remains the only contractual agent surface, stable gateway attachability is published through the shared runtime-owned publisher before live attach, current-session attach becomes valid only after matching registration, and later same-session gateway attach preserves or restores that reserved surface.

## Impact

- Affected code includes the `houmao-srv-ctrl` command tree, pair launch artifact publication, managed-agent gateway attach routing in `houmao-server`, live gateway state persistence, same-session gateway launcher and tmux lifecycle handling for `houmao_server_rest`, and pair-managed tmux surface resolution.
- Affected observability surfaces include tmux attach expectations, gateway logging, current-session discovery from tmux env, and pair-managed helper flows that must keep following the explicit agent surface instead of whichever window is selected.
- Affected documentation and tests include pair CLI usage, managed-agent gateway lifecycle guidance, launch-time attachability publication, tmux topology guidance for `houmao_server_rest`, and verification for the two attach modes plus preserved window-`0` behavior.
