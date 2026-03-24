## 1. Pair CLI and attach resolution

- [x] 1.1 Add a pair-owned `houmao-srv-ctrl agent-gateway` command group and `attach` verb for pair-managed `houmao_server_rest` sessions rather than relying on the legacy runtime CLI surface.
- [x] 1.2 Implement explicit-target attach mode (`--agent <agent-ref>`) by resolving through the managed-agent alias space and routing attach through the Houmao managed-agent gateway lifecycle API.
- [x] 1.3 Implement current-session attach mode (no `--agent`) by resolving the current tmux session, requiring stable Houmao gateway attachability env pointers, loading a readable `houmao_server_rest` attach contract, using its persisted `api_base_url` plus `session_name` as the authoritative managed-agent target, and refusing attach when those envs are missing, stale, ambiguous, identify a non-`houmao_server_rest` session, or fail to resolve exactly one managed agent on that persisted server.

## 2. Pair launch capability and same-session topology

- [x] 2.1 Reuse the existing runtime-owned gateway publication seam to seed `attach.json`, offline gateway state, queue/bootstrap assets, and stable gateway tmux env pointers for delegated `houmao_server_rest` pair launches and registrations before any live gateway is attached, and make current-session attach valid only after the matching managed-agent registration succeeds.
- [x] 2.2 Implement same-session gateway auxiliary-window launch plus the authoritative live execution-handle contract in `<session-root>/gateway/run/current-instance.json`, including execution mode and tmux window/pane identity for `houmao_server_rest`, while keeping `houmao-server` and its internal child-CAO support state outside the agent tmux session.
- [x] 2.3 Preserve tmux window `0` as the only contractual agent surface for pair-managed sessions, including attach, detach, crash cleanup, auxiliary-window recreation, and same-session relaunch-to-window-0 behavior.

## 3. Pair-managed tmux observers, docs, and verification

- [x] 3.1 Update pair-managed tmux resolvers, the server-side managed-agent tmux tracking and transport-resolution path, transport fallbacks, and repo-owned helpers that would otherwise follow the selected active pane to follow the explicit agent surface in window `0` instead.
- [x] 3.2 Add unit and integration coverage for explicit attach mode, current-session attach mode using persisted `api_base_url` plus `session_name`, refusal when stable gateway env is absent, stale, or pre-registration, same-session execution-handle persistence and recreation in `gateway/run/current-instance.json`, same-session auxiliary-window behavior for `houmao_server_rest`, and preserved window-`0` behavior across gateway lifecycle changes.
- [x] 3.3 Update pair, gateway, runtime, and troubleshooting docs to describe `houmao-srv-ctrl agent-gateway`, the two attach modes, the authoritative current-session attach contract fields, launch-time attachability publication through the shared runtime seam, the registration-dependent readiness boundary, same-session `houmao_server_rest` gateway windows, and the intentionally non-contractual nature of non-zero windows.
