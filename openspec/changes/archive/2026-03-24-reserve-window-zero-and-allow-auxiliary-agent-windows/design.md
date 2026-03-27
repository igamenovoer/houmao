## Context

The future operator-facing boundary is the Houmao pair, not the raw runtime CLI and not raw `cao_rest`. Pair-managed TUI sessions already persist `backend = "houmao_server_rest"` so callers can talk to `houmao-server` and ignore the child-CAO implementation details behind that public contract. The current gateway story does not fully match that direction yet:

- `houmao-srv-ctrl` has no native `agent-gateway` command, so pair users still have to think in terms of runtime-side attach behavior;
- delegated pair launches publish manifest and identity discovery state, but they do not yet seed stable gateway attachability pointers early enough for a no-identity "run this from inside the managed tmux session" workflow; and
- gateway attach still behaves like an out-of-band detached sidecar rather than a pair-owned lifecycle that can place the gateway in an auxiliary tmux window while preserving one stable agent surface.

The earlier draft of this change treated `cao_rest` and tmux-backed headless sessions as the same-session topology targets while keeping `houmao_server_rest` out-of-session. That no longer fits the intended product direction. If `houmao-srv-ctrl` is the public replacement and should behave as if raw CAO runtime identities do not exist, the same-session auxiliary-window story needs to center on pair-managed `houmao_server_rest` sessions instead.

This revised change therefore shifts the boundary:

- `houmao-srv-ctrl` owns the user-facing gateway attach command;
- pair-managed TUI sessions with `backend = "houmao_server_rest"` are the same-session topology target;
- `houmao-server` remains the public authority and stays outside the agent tmux session; and
- tmux window `0` remains the only contractual agent surface while non-zero windows stay implementation-owned.

## Goals / Non-Goals

**Goals:**

- Make `houmao-srv-ctrl agent-gateway` the pair-owned gateway lifecycle surface for pair-managed `houmao_server_rest` sessions.
- Support two attach modes: explicit target mode with `--agent`, and current-session mode without `--agent` that infers from stable tmux-published Houmao gateway env and fails closed when that discovery is unavailable.
- Keep attach execution Houmao-owned by routing pair CLI attach through `houmao-server` managed-agent gateway lifecycle instead of through raw runtime or raw CAO attach semantics.
- Allow supported pair-managed `houmao_server_rest` sessions to host the gateway sidecar in an auxiliary tmux window in the same managed agent session.
- Reserve tmux window `0` as the only contractual agent surface in that same-session layout.
- Seed stable gateway capability and tmux env pointers during pair launch or launch registration so current-session attach works before any live gateway exists.
- Preserve or restore the reserved agent window `0` across gateway attach, detach, crash cleanup, and same-session relaunch.
- Keep non-zero tmux windows non-contractual.

**Non-Goals:**

- Make `houmao-srv-ctrl` publicly manage raw `cao_rest` sessions or require users to think in terms of raw CAO runtime identities.
- Move the `houmao-server` process or its internal child-CAO support state into the agent's tmux session.
- Make non-zero window names, indices, or counts part of the public contract.
- Replace durable gateway log files with tmux-only observability.
- Redesign the managed-agent identity model or `/houmao/agents/*` payloads beyond what is needed to support pair-owned gateway attach.

## Decisions

### Decision 1: `houmao-srv-ctrl` publicly manages pair-owned `houmao_server_rest`, not raw `cao_rest`

The public CLI surface for this change is `houmao-srv-ctrl`, and its gateway lifecycle scope is pair-managed `houmao_server_rest` sessions only. Even under the explicit `cao` subgroup, the pair should continue to behave as if raw `cao-server` / `cao_rest` are implementation details rather than public runtime identities.

Rationale:

- The pair docs already define `houmao-server` as the public authority and `houmao-srv-ctrl` as the pair CLI.
- Pair-launched TUI sessions already persist `backend = "houmao_server_rest"` instead of `cao_rest`.
- Keeping `cao_rest` out of the pair-owned gateway lifecycle avoids reintroducing the raw CAO abstraction through a new top-level pair command.

Alternatives considered:

- Keep `houmao-srv-ctrl agent-gateway` generic across `cao_rest` and `houmao_server_rest`. Rejected because it weakens the pair boundary and makes raw CAO runtime identities user-visible again.
- Leave gateway lifecycle on `houmao-cli` for pair sessions. Rejected because the intended future boundary is the pair CLI, not the legacy runtime CLI.

### Decision 2: `houmao-srv-ctrl agent-gateway` becomes the public pair-owned command surface

The pair CLI will gain an `agent-gateway` command group. The first required verb is `attach`, but the group boundary is intentional so later pair-owned verbs such as `status`, `detach`, `send-prompt`, `interrupt`, or notifier control can live under one stable namespace instead of recreating the old flat runtime CLI shape.

The required attach forms are:

- `houmao-srv-ctrl agent-gateway attach --agent <agent-ref>`
- `houmao-srv-ctrl agent-gateway attach`

Rationale:

- A grouped surface gives the pair a stable migration target rather than a one-off attach command.
- The two attach forms correspond directly to the operator workflows the user wants: explicit target and current-session attach.

Alternatives considered:

- Add only a single `attach-gateway` top-level command. Rejected because it repeats the legacy runtime CLI shape and makes later pair-owned gateway verbs awkward.

### Decision 3: Pair CLI attach resolves and executes through Houmao-managed authority

`houmao-srv-ctrl agent-gateway attach` will be a client of the Houmao managed-agent gateway lifecycle, not a raw local runtime attach wrapper.

Explicit target mode:

- requires `--agent <agent-ref>`;
- resolves the target through the managed-agent alias space already exposed by `houmao-server`; and
- executes attach through `POST /houmao/agents/{agent_ref}/gateway/attach`.

Current-session mode:

- requires execution inside tmux;
- resolves the current tmux session via `tmux display-message -p '#S'`;
- validates stable Houmao gateway attachability from the current tmux session environment, especially `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`;
- requires those pointers to resolve to a readable `houmao_server_rest` attach contract;
- treats that contract's persisted `api_base_url` and `backend_metadata.session_name` as the authoritative server authority and managed-agent route target for no-`--agent` mode;
- fails closed when that persisted authority or alias does not resolve exactly one managed agent on that server; and
- then executes attach through the same managed-agent gateway attach route rather than bypassing the server.

If current-session mode cannot validate those env pointers, or if the persisted server and session alias no longer resolve, it fails explicitly. It does not guess from cwd, ambient shell env, raw CAO state, `terminal_id`, or other aliases.

Rationale:

- The pair should keep `houmao-server` as the public authority for managed-agent gateway lifecycle.
- Tmux session env is the stable source of truth for current-session discovery; ambient process env inside an already-running pane is not reliable enough.
- Using one managed-agent route for both modes keeps attach semantics consistent across pair-managed TUI and managed headless sessions.

Alternatives considered:

- Let current-session mode perform a local runtime attach without involving `houmao-server`. Rejected because it breaks the pair abstraction and creates two authorities for the same gateway lifecycle.
- Fall back from missing tmux gateway env to cwd or generic tmux-session heuristics. Rejected because that makes current-session attach ambiguous and unsafe.

### Decision 4: Pair launch seeds gateway capability through the shared runtime publisher before live attach, and current-session attach becomes valid only after registration

Delegated pair launches for `houmao_server_rest` must publish stable gateway capability before any live gateway exists. That publication must reuse the existing runtime-owned gateway capability seam so one shared publisher continues to own `gateway/attach.json`, `gateway/state.json`, queue/bootstrap assets, and the tmux session env pointers `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`.

This publication must happen during pair launch or launch registration, not only on the first attach action, so that current-session attach works from inside the managed tmux session without requiring an explicit agent identity.

However, a pair-managed session is not considered current-session attach-ready until both of the following are true for the same persisted `api_base_url` and `session_name`:

- the shared gateway publication seam has materialized the stable attachability artifacts and tmux env pointers; and
- `houmao-server` managed-agent registration has succeeded for that session.

If publication has happened but registration has not, current-session attach must fail closed as invalid or stale current-session metadata rather than retrying with another authority or alias.

Rationale:

- Current-session attach depends on stable attachability being present before live attach.
- Reusing the existing runtime-owned gateway publication seam keeps one authoritative writer for attachability artifacts instead of splitting ownership between runtime and pair layers.
- Pair launch and managed-agent registration are separate steps today, so the no-`--agent` readiness boundary must be explicit.
- The repo already separates "gateway-capable but not attached" from "live gateway attached"; the pair path should adopt that same contract instead of inventing a second discovery model.

Alternatives considered:

- Hand-roll a pair-specific gateway artifact writer. Rejected because the repo already has a runtime-owned publication seam for attachability artifacts and a second writer would split authority.
- Publish stable gateway env only on first attach. Rejected because current-session attach would have no stable discovery anchor.
- Require `--agent` for every pair attach. Rejected because it gives up the tmux-local workflow the user explicitly wants.

### Decision 5: Same-session auxiliary-window topology applies to the managed `houmao_server_rest` agent session, not to the server process

The same-session auxiliary-window topology target is the managed agent tmux session owned by the pair-managed `houmao_server_rest` session. The gateway sidecar may run in an auxiliary tmux window of that agent session. The `houmao-server` process and its internal child-CAO support state remain outside that tmux session.

Tmux window `0` is the only contractual slot in this topology. The agent process must remain in window `0`. Non-zero windows remain implementation-owned: their names, indices, and counts are not part of the public contract.

Rationale:

- The operator attaches to the managed agent session, not to the `houmao-server` process.
- The requested observability mode is about seeing the gateway next to the agent surface, not about moving the control plane server into the agent container.
- Keeping only window `0` contractual preserves flexibility for auxiliary windows.

Alternatives considered:

- Keep `houmao_server_rest` on detached gateway topology forever. Rejected because `houmao_server_rest` is the pair-owned TUI path and should support the observability mode the pair is supposed to own.
- Move `houmao-server` or child-CAO helper processes into the agent's tmux session. Rejected because that collapses the control-plane boundary into the operator-facing agent surface.

### Decision 6: Same-session gateway lifecycle uses a persisted tmux-owned execution handle plus gateway health

For same-session mode, the runtime will persist one authoritative live gateway execution record under `<session-root>/gateway/run/current-instance.json` and will treat the auxiliary tmux window and pane recorded there as the authoritative local execution surface for the gateway.

That runtime-owned live record continues to carry the listener host, port, and managed-agent instance identity. In same-session mode it also carries an explicit execution mode plus the tmux window and pane identifiers for the auxiliary gateway surface. Detached mode continues to carry detached-process identity in the same authoritative live record.

Detach, crash cleanup, and auxiliary-window recreation must resolve the live gateway surface from that runtime-owned record rather than from ad hoc tmux discovery over non-contractual auxiliary windows. Local liveness will come from tmux-owned pane state such as `pane_pid` or `pane_dead`, readiness will still require successful gateway health responses, and shutdown or cleanup will target that recorded auxiliary tmux surface rather than pretending the gateway is backed by a detached `Popen` lifecycle.

Durable gateway artifacts remain under `<session-root>/gateway/`, and `gateway.log` remains the durable operator log even when the same stream is also visible in the auxiliary tmux window.

Rationale:

- The repo already treats one live gateway state file under `gateway/run/` as authoritative; evolving that seam is more native than inventing a second execution-handle registry or relying on runtime heuristics.
- Same-session launch cannot keep relying on `subprocess.Popen` as the local lifecycle boundary.
- Tmux already exposes the pane metadata needed to identify whether the foreground gateway process is still alive.
- Gateway HTTP health remains the right readiness check even in same-session mode.

Alternatives considered:

- Rediscover the auxiliary tmux gateway surface ad hoc on every detach or cleanup. Rejected because non-zero tmux windows are intentionally non-contractual and heuristic rediscovery would make cleanup and recreation fragile.
- Use HTTP health alone as both readiness and liveness. Rejected because a purely HTTP-driven model loses local execution ownership once the process has crashed or never bound.
- Preserve a detached launcher for `houmao_server_rest` while only changing the CLI surface. Rejected because it would not satisfy the requested same-session auxiliary-window observability mode.

### Decision 7: Pair-managed helpers, routing, and recovery follow the explicit agent surface, not the selected window

Any pair-managed tmux resolver, server-side managed-agent TUI tracker or tmux transport resolution path, control fallback, or repo-owned helper that would otherwise follow the selected active pane must be updated to resolve the explicit agent surface in window `0` when the session uses same-session auxiliary windows.

Gateway attach, detach, crash cleanup, and auxiliary-window recreation must only affect the auxiliary process window. They must not kill or repurpose the reserved agent window `0`.

If the agent process later disappears unexpectedly and the runtime relaunches it inside the same tmux session, the recovery path must restore the relaunched agent process to window `0` before the session is treated as recovered or ready again.

Rationale:

- Once the gateway can be visible in another window, "selected window" is no longer a safe proxy for "agent surface."
- The user's requested contract is stable agent surface in window `0`, not whichever window happens to be foregrounded.
- Preserving or restoring window `0` keeps lifecycle semantics predictable across same-session sidecar changes.

Alternatives considered:

- Leave helper behavior unchanged and document that foreground gateway windows may confuse pair-managed tooling. Rejected because it makes the new topology unreliable in practice.

## Risks / Trade-offs

- Pair current-session attach now depends on launch-time publication of stable gateway env pointers. Mitigation: make capability publication an explicit part of pair launch/registration rather than a best-effort late attach side effect.
- Routing attach through `houmao-server` adds one more layer between the CLI and the tmux session. Mitigation: keep identity resolution explicit, reuse managed-agent aliases, and keep error messages concrete about missing env, ambiguous identity, or unavailable runtime control.
- Same-session auxiliary windows can expose hidden "follow active pane" assumptions in pair-managed tooling. Mitigation: centralize explicit agent-surface resolution and add regression coverage for selected auxiliary windows.
- The same-session gateway launcher adds lifecycle complexity relative to the detached `Popen` model. Mitigation: isolate the same-session execution handle at the attach layer and keep durable storage plus health readiness contracts unchanged.

## Migration Plan

1. Update the change artifacts and delta specs so the public gateway lifecycle surface is `houmao-srv-ctrl agent-gateway`, scoped to pair-managed `houmao_server_rest` sessions with explicit-target and current-session attach modes.
2. Seed stable gateway capability and tmux env pointers during delegated pair launch or registration through the shared runtime-owned publication seam, and make current-session attach valid only after the matching managed-agent registration succeeds.
3. Add the `houmao-srv-ctrl agent-gateway` group and route attach through the Houmao managed-agent gateway API for explicit and current-session modes.
4. Implement same-session gateway auxiliary-window launch plus the persisted live execution-handle contract in `gateway/run/current-instance.json`, along with readiness, liveness, and teardown for `houmao_server_rest`, while keeping `houmao-server` and internal child-CAO state out of the agent tmux session.
5. Update pair-managed tmux surface resolution, including the server-side managed-agent tracking and transport-resolution path, tests, and docs so auxiliary windows remain observable without redefining the agent surface in window `0`.

Rollback strategy:

- Keep `houmao-srv-ctrl agent-gateway` as the public pair-owned surface if introduced, but fall back to detached gateway topology for `houmao_server_rest`.
- Preserve launch-time gateway capability publication when it is already correct, since current-session validation and offline gateway status remain useful independently of same-session window hosting.
- Do not roll back to a model where pair users must think in terms of raw `cao_rest` or raw `cao-server` identities to attach a gateway.

## Open Questions

None at proposal time. The revised direction is now explicit: the pair CLI owns the public gateway lifecycle, `houmao_server_rest` is the same-session topology target, current-session attach depends on stable tmux-published Houmao gateway env, and raw `cao_rest` is out of scope for the pair-owned command surface.
