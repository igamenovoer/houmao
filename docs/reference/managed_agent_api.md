# Managed-Agent API

`/houmao/agents/*` exposes discovery, observation, and control for managed agents. The shared registry records each agent's run mode and backend. Observation uses the evidence available to the owner in that mode. Durable headless turn artifacts remain available through `/turns/*`.

`houmao-passive-server` is the maintained shared coordination plane for this surface. An attached healthy gateway becomes the live per-agent control plane behind that same public API. Callers do not switch route families when a gateway attaches; passive-server keeps the public contracts stable and changes only the backing control path.

For the maintained server boundary that exposes these routes, use [houmao-passive-server](cli/houmao-passive-server.md). For passive-server listener and headless state layout, use the passive-server runtime layout section in that page. For the live sidecar HTTP surface that the managed-agent gateway routes project or proxy, use [Agent Gateway Reference](gateway/index.md).

## Route Families

| Surface | Routes | Applies to | Notes |
| --- | --- | --- | --- |
| Discovery and curated state | `GET /houmao/agents`, `GET /houmao/agents/{agent_ref}`, `GET /houmao/agents/{agent_ref}/managed-state`, `GET /houmao/agents/{agent_ref}/managed-history` | Managed agents with verified observations | Returns the operating mode, shared posture, and bounded history where supported |
| Curated detail | `GET /houmao/agents/{agent_ref}/managed-state/detail` | Managed agents with verified observations | Returns a common envelope with mode-specific detail |
| Mode-specific observation | `GET /houmao/agents/{agent_ref}/state`, `GET /houmao/agents/{agent_ref}/state/detail`, `GET /houmao/agents/{agent_ref}/history` | According to live capability | Use raw TUI state only for verified terminal surfaces. Web state uses the bound browser session. |
| Transport-neutral request submission | `POST /houmao/agents/{agent_ref}/requests` | TUI and headless | Official prompt and interrupt surface across both transports |
| Finalized usage | `GET /houmao/agents/{agent_ref}/usage` | Headless and qualified TUI sources | Returns stable accounting records, capability/collection health, and a resumable cursor; active turns are excluded |
| Gateway proxy, direct prompt control, raw gateway-owned TUI inspection, gateway-mediated requests, headless session control, and notifier control | `GET /houmao/agents/{agent_ref}/gateway`, `POST /houmao/agents/{agent_ref}/gateway/attach`, `POST /houmao/agents/{agent_ref}/gateway/detach`, `POST /houmao/agents/{agent_ref}/gateway/control/prompt`, `GET /houmao/agents/{agent_ref}/gateway/control/headless/state`, `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session`, `GET /houmao/agents/{agent_ref}/gateway/tui/state`, `GET /houmao/agents/{agent_ref}/gateway/tui/history`, `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`, `POST /houmao/agents/{agent_ref}/gateway/requests`, `GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier` | TUI and headless | `POST /gateway/control/prompt` is immediate "send now or refuse now" control; `POST /gateway/requests` remains the queued gateway surface; `gateway/control/headless/*` is headless only; passive-server returns not-implemented for remote gateway attach/detach because those remain same-host manager operations |
| Pair-owned mailbox follow-up | `GET /houmao/agents/{agent_ref}/mail/status`, `GET /houmao/agents/{agent_ref}/mail/resolve-live`, `POST /houmao/agents/{agent_ref}/mail/list`, `POST /houmao/agents/{agent_ref}/mail/peek`, `POST /houmao/agents/{agent_ref}/mail/read`, `POST /houmao/agents/{agent_ref}/mail/send`, `POST /houmao/agents/{agent_ref}/mail/post`, `POST /houmao/agents/{agent_ref}/mail/reply`, `POST /houmao/agents/{agent_ref}/mail/mark`, `POST /houmao/agents/{agent_ref}/mail/move`, `POST /houmao/agents/{agent_ref}/mail/archive` | TUI and headless when mailbox capability is present | These routes require pair-owned mailbox capability plus an eligible live gateway |
| Stop, native headless lifecycle, and durable turn detail | `POST /houmao/agents/{agent_ref}/stop`, `POST /houmao/agents/headless/launches`, `POST /houmao/agents/{agent_ref}/turns`, `POST /houmao/agents/{agent_ref}/interrupt`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout`, `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr` | Stop applies to TUI and headless; turn detail is headless only | TUI stop reuses the managed session-delete lifecycle; durable headless turn evidence stays on `/turns/*` |

## Identity And Alias Resolution

`tracked_agent_id` is the canonical managed-agent identity returned by the API. Route lookups also resolve through explicit aliases when they are unique.

Supported aliases include:

- `tracked_agent_id`
- TUI `terminal_id`
- TUI `session_name`
- runtime `runtime_session_id` when present
- `agent_name`
- `agent_id`

Alias resolution applies consistently across `GET /houmao/agents/{agent_ref}`, `/managed-state`, `/managed-state/detail`, `/managed-history`, the raw observation routes, `/requests`, `/stop`, `/gateway/*`, and `/mail/*`. Ambiguous aliases return a conflict.

## Summary State

Use `GET /houmao/agents/{agent_ref}/managed-state` for orchestration, availability checks, and quick inspection across run modes.

The response includes:

- `identity`: transport discriminator plus managed-agent identity fields
- `availability`: coarse operability summary
- `turn`: shared current-turn posture and optional active turn id
- `last_turn`: shared coarse result summary
- `diagnostics`: structured availability or recovery details
- `control` and `capabilities` when the current owner supplies managed control evidence
- `mailbox`: redacted mailbox posture when the managed agent has mailbox support
- `gateway`: redacted gateway posture when gateway capability is known

Representative summary behavior:

- TUI agents expose coarse turn posture without requiring callers to interpret the raw tracked terminal payload.
- Headless agents expose coarse turn posture without requiring callers to read raw turn artifacts.
- When an attached gateway is healthy, summary and detail projection prefer the gateway HTTP read surface.
- When no live gateway is attached, or when direct fallback is the only safe option, the same routes continue projecting from passive observation or runtime state.
- `/managed-history` returns a bounded posture history where supported. Durable headless events remain on `/turns/*`.

### Local Manager State

`houmao-mgr agents single --agent-id <id> state` selects the registry record and checks its saved manifest before observing the runtime. The response keeps registry lifecycle in `identity.lifecycle_state`. In JSON, `publication` carries the recorded lifecycle timestamp and lease evidence. Read `availability`, `control.source`, `control.freshness`, and `control.observed_at_utc` for the observation. An active or fresh registry record confirms publication.

Web and service state use their verified native owner even when the supervisor socket is inaccessible. TUI state uses a current, matching gateway tracker observation when available. Otherwise, the manager reads the exact primary pane on the recorded owner socket. When that observation fails, reported identity and redacted mailbox summaries remain available, and live turn posture and prompt readiness are unknown.

Headless state reads the saved turn outcome independently of current admission. Headless detail reports `tmux_session_live` and `can_accept_prompt_now` as `null` when the evidence cannot establish them. The normal prompt command checks admission at the selected owner.

## Detailed State

`GET /houmao/agents/{agent_ref}/managed-state/detail` returns the shared envelope with these fields.

- `tracked_agent_id`
- `identity`
- `summary_state`
- `detail`

`detail` is discriminated by `transport`.

### TUI Detail

The curated TUI detail includes these fields.

- `terminal_id`
- `canonical_terminal_state_route`
- `canonical_terminal_history_route`
- tracked `diagnostics`
- optional `probe_snapshot`
- optional `parsed_surface`
- tracked `surface`
- `stability`

The maintained raw passive TUI inspection surface is exposed through `/houmao/agents/{agent_ref}/state/detail`. When an attached gateway owns live tracking, the exact raw gateway-owned inspection surface is exposed separately through `/houmao/agents/{agent_ref}/gateway/tui/state` and `/houmao/agents/{agent_ref}/gateway/tui/history`.

For attached eligible TUI sessions, the live tracked state served here is gateway-owned and projected back through passive-server. When no live gateway owns that session, passive-server falls back to its registry-driven observer.

### Headless Detail

Headless detail is execution-centric and intentionally does not fabricate TUI parser concepts. It includes:

- `runtime_resumable`
- `tmux_session_live`
- `can_accept_prompt_now`
- `interruptible`
- optional `chat_session` state with `current`, `startup_default`, and gateway-owned `next_prompt_override` when that view is sourced from a live gateway-backed control plane
- shared `turn`
- shared `last_turn`
- `active_turn_started_at_utc`
- `active_turn_interrupt_requested_at_utc`
- `last_turn_status`
- `last_turn_started_at_utc`
- `last_turn_completed_at_utc`
- `last_turn_completion_source`
- `last_turn_returncode`
- `last_turn_history_summary`
- `last_turn_error`
- optional redacted `mailbox`
- optional redacted `gateway`
- structured `diagnostics`

This route is the canonical rich inspection surface for managed headless agents when a caller needs current runtime posture without scraping `stdout`, `stderr`, or exit-code files.

`tmux_session_live` is diagnostic only. Terminal headless status, readiness for the next managed prompt, and last-turn timestamps reconcile from authoritative active-turn state plus durable turn artifacts such as the persisted `exitcode` file. `last_turn_completion_source` remains optional diagnostic metadata when it can be recovered.

For attached healthy headless gateways, passive-server reads live control posture from the gateway HTTP surface before building this response. Durable turn records and turn reconciliation still remain passive-server-owned when passive-server owns the headless agent.

### Web and Service Detail

Web detail reports availability, readiness, and the latest native turn for the verified browser session. The observer can use the owner-bound native session directly when the gateway is detached. Public discovery includes the browser handoff URL without private control credentials.

The service detail schema reports supervisor liveness, native connection state, and request correlation separately. Read `capabilities.operations` to determine what the selected adapter supports.

## Transport-Neutral Request Submission

`POST /houmao/agents/{agent_ref}/requests` is the official prompt and interrupt surface across both transports.

The request body is typed by `request_kind`.

Prompt submission:

```json
{
  "request_kind": "submit_prompt",
  "prompt": "Summarize the current state.",
  "execution": {
    "model": {
      "name": "claude-3-7-sonnet",
      "reasoning": {
        "level": 7
      }
    }
  }
}
```

Interrupt submission:

```json
{
  "request_kind": "interrupt"
}
```

Accepted responses use one shared envelope:

```json
{
  "success": true,
  "tracked_agent_id": "claude-headless-1",
  "request_id": "mreq-123",
  "request_kind": "submit_prompt",
  "disposition": "accepted",
  "detail": "accepted",
  "headless_turn_id": "turn-1",
  "headless_turn_index": 1
}
```

Important rules:

- `disposition` is `accepted` when the request caused or targeted real work, and `no_op` when an interrupt request found no active interruptible work.
- `headless_turn_id` and `headless_turn_index` are present only when the accepted request created or targeted a managed headless turn.
- TUI prompt submission prefers a healthy attached gateway and falls back to the direct transport only when no live gateway currently owns safe prompt admission for that session.
- Headless prompt submission keeps passive-server-owned durable turn creation and turn-record authority, then prefers attached gateway admission when a healthy gateway owns live headless control.
- Headless prompt routes accept optional request-scoped `execution.model.name` plus optional `execution.model.reasoning.level` as a tool/model-specific preset index.
- Request-scoped execution overrides merge with launch-resolved defaults for the current headless turn only and never rewrite the stored manifest or later live state.
- TUI-backed prompt submission rejects any `execution` payload with HTTP `422` instead of silently dropping it.
- Discovery of a gateway does not change the public request contract; callers still use `/houmao/agents/{agent_ref}/requests`.

Observable admission and failure semantics:

- HTTP `422`: invalid request shape or other request validation failure
- HTTP `409`: headless prompt submission conflicts with an already-active managed headless turn
- HTTP `503`: the addressed managed agent is not currently operable for the requested action
- HTTP `200` with `disposition = "no_op"`: an interrupt request found no active interruptible TUI or headless work

The dedicated `POST /houmao/agents/{agent_ref}/interrupt` route still exists for headless-only best-effort interrupt delivery, but new cross-transport callers should prefer `POST /houmao/agents/{agent_ref}/requests`.

## Gateway Lifecycle, Gateway-Mediated Requests, And Notifier Control

Selected-agent HTTP operations resolve canonical owner policy even when the gateway is detached. A valid empty administrator roster grants every supported client action. With a keyed roster, the server checks each action against the caller's verified permissions or the applicable default group. Verbatim prompts and interrupts require `agent.prompt.direct` and `agent.interrupt`, respectively. Qualified slash commands also require `agent.command.invoke`. Passive stop requires `agent.stop`. A detailed state response requires `agent.status.read` and `agent.state.detail.read`.

Use `GET /houmao/agents/{agent_ref}/auth/endpoint` to retrieve the target generation, current passive listener, and challenge path. For a signed call, request proof at that path and sign the exact passive method, path, query, and body. The typed `PassiveServerClient` checks the endpoint and challenge against its configured target before signing.

The passive server rechecks the admitted decision before direct disclosure or handoff. When it forwards an operation, it creates a short-lived, one-use relay for the exact downstream request and live gateway instance. The receiving gateway rechecks the caller's current authority. An unsigned open-mode request keeps anonymous attribution, and enrolling the first admin ends earlier open-mode grants even if the roster later becomes empty.

HTTP 401 indicates that proof is required or invalid and supplies the passive challenge path. HTTP 403 indicates insufficient authority. HTTP 503 indicates unavailable policy. A refused call ends before fallback. Admitted gateway attach and detach calls return HTTP 501 and direct the caller to the owner-side `houmao-mgr` command.

Server-managed backing calls use their own owner-service credential for the exact internal request. The credential remains valid across changes to the client roster and can be used only with its configured target and operation. Keep the global passive-server administration surface isolated from remote publication. [Gateway Access and Remote Deployment](gateway/operations/access.md)

Managed-agent gateway routes project the same gateway status, raw TUI tracking state, prompt-note provenance hook, and notifier state used by the live sidecar.

`GET /houmao/agents/{agent_ref}/gateway` returns the same `GatewayStatusV1` shape used by the direct gateway status surface. It can therefore report a seeded offline `not_attached` status even when no live sidecar exists yet.

`POST /houmao/agents/{agent_ref}/gateway/attach` is present on passive-server for route-shape compatibility but returns not implemented. Gateway attach and detach are same-host operations; use `houmao-mgr agents single --agent-id <id> gateway attach|detach` or `houmao-mgr agents self gateway attach|detach` on the host that owns the tmux session.

Important attach behavior:

- local attach is idempotent when a healthy live gateway is already attached for the same managed agent
- local attach accepts optional `tui_tracking_timings` with positive-second overrides for `watch_poll_interval_seconds`, `stability_threshold_seconds`, `completion_stability_seconds`, `unknown_to_stalled_timeout_seconds`, `stale_active_recovery_seconds`, and `final_stable_active_recovery_seconds`. `stale_active_recovery_seconds` governs how long the gateway waits before treating a stuck active turn as stale; this is related to but distinct from the managed-agent recovery system that handles broken tmux sessions. See [Degraded and Stale Active Recovery](run-phase/degraded-stale-recovery.md).
- same-session attach resolves the current tmux session from `HOUMAO_MANIFEST_PATH` first and from `HOUMAO_AGENT_ID` plus shared registry as a fallback
- explicit attach resolves the group-level `agents single --agent-name <friendly-name>` or `agents single --agent-id <authoritative-id>` selector through maintained manager targeting rules

`POST /houmao/agents/{agent_ref}/gateway/detach` is likewise not a remote passive-server action. Use local manager detach on the owning host.

The manager uses the verified owner route for lifecycle operations during a gateway outage. An exact managed ID selects the same saved execution context for inspection, stop, and relaunch.

```bash
houmao-mgr agents single --agent-id "$AGENT_ID" gateway detach
houmao-mgr agents single --agent-id "$AGENT_ID" state
houmao-mgr agents single --agent-id "$AGENT_ID" stop
houmao-mgr agents single --agent-id "$AGENT_ID" relaunch
```

`GET /houmao/agents/{agent_ref}/gateway/tui/state` proxies the raw `HoumaoTerminalStateResponse` exposed by the live gateway tracker for that managed agent.

`GET /houmao/agents/{agent_ref}/gateway/tui/history` proxies the gateway-owned bounded in-memory snapshot-history surface. This route is intentionally different from coarse managed-agent `/history` and from terminal transition `/history`: it returns recent raw tracked snapshots, capped in memory by the live gateway tracker.

`POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt` records explicit prompt-note provenance on the live gateway tracker without enqueueing a gateway request.

`POST /houmao/agents/{agent_ref}/gateway/requests` proxies live gateway `submit_work_request`, `submit_prompt`, and `interrupt` requests. A detached gateway yields an unavailable result. For `submit_prompt`, headless targets accept the optional `execution.model` override. TUI targets return HTTP 422 for that override.

`POST /houmao/agents/{agent_ref}/work-requests` delivers one immediate wrapped request to a ready, passive-managed DSH Headless agent with a detached gateway. Send `{"kind":"submit_work_request","payload":{"text":"Review PR 42"}}` under `agent.request.submit`. Passive ingress keeps verified or anonymous attribution, quotes the text, and uses the current conversation and configured model. It rechecks authority, generation, and detachment before native handoff. The receipt contains `request_id` and `outcome`. `handed_off` confirms native delivery. `not_sent` indicates a known refusal. `unknown` indicates that handoff could not be confirmed. Private turn output requires separate access.

Choose the gateway proxy or direct passive route before submitting the request. A refusal applies to that attempt. To contact a detached agent through its mailbox, send ordinary mail under the recipient's mail policy.

`POST /houmao/agents/{agent_ref}/gateway/control/prompt` is the immediate "send now or refuse now" gateway-control surface. It accepts the same optional headless-only `execution.model.name` plus optional `execution.model.reasoning.level` (`>=0`, interpreted against the resolved tool/model ladder) payload as the queued `submit_prompt` surface, applies the override to exactly the current prompt admission, and rejects the request with HTTP `422` when the resolved target is TUI-backed. Partial overrides merge with launch-resolved defaults through the shared headless resolution helper.

`POST /houmao/agents/{agent_ref}/gateway/control/send-keys` proxies the live gateway raw control-input route. It carries the same `<[key-name]>` grammar and `escape_special_keys` behavior as the direct gateway `POST /v1/control/send-keys` contract.

`GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier` proxy the live gateway notifier control surface for that managed agent. These routes require a live attached gateway; they return HTTP `503` when no live gateway is currently attached or when the live gateway health check fails. The proxy preserves notifier `appendix_text` unchanged: status returns the live gateway's effective appendix, omitted fields stay omitted on `PUT`, non-empty strings replace the runtime appendix, and `appendix_text=""` clears it. Status also returns the effective `context_error_policy` and `pre_notification_context_action`. `PUT` accepts those fields to select degraded-context handling and optional pre-notification compaction through the live gateway contract.

The default documented prompt path is `houmao-mgr agents single --agent-name <friendly-name> prompt ...` for selected agents or `houmao-mgr agents self prompt ...` for the current managed session over `POST /houmao/agents/{agent_ref}/requests`. That surface keeps working across direct and gateway-backed control modes. `houmao-mgr agents single --agent-name <friendly-name> gateway prompt ...` is the explicit gateway-mediated alternative when live-gateway admission and queue semantics matter and the caller wants to require a live gateway instead of letting the server choose the safe backing path. Scoped gateway `send-keys`, `tui`, and `mail-notifier` commands use `agents single ... gateway ...` for selected-agent targeting and `agents self gateway ...` for current-session targeting. When a friendly name is ambiguous, operators should retry with `--agent-id <authoritative-id>`.

## Pair-Owned Mail Follow-Up

`GET /houmao/agents/{agent_ref}/mail/status`, `GET /houmao/agents/{agent_ref}/mail/resolve-live`, `POST /houmao/agents/{agent_ref}/mail/list`, `POST /houmao/agents/{agent_ref}/mail/peek`, `POST /houmao/agents/{agent_ref}/mail/read`, `POST /houmao/agents/{agent_ref}/mail/send`, `POST /houmao/agents/{agent_ref}/mail/post`, `POST /houmao/agents/{agent_ref}/mail/reply`, `POST /houmao/agents/{agent_ref}/mail/mark`, `POST /houmao/agents/{agent_ref}/mail/move`, and `POST /houmao/agents/{agent_ref}/mail/archive` let callers perform mailbox follow-up through the managed-agent API without discovering the live gateway host or port.

Important boundary rules:

- these routes require pair-owned mailbox capability on the addressed managed agent
- they also require an eligible live gateway to be attached
- they coexist with `GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `gateway/mail-notifier` remains background notifier configuration, while `mail/*` is the foreground mailbox-operation surface
- `POST /mail/read` reads one selected message and marks it read, while `POST /mail/mark`, `POST /mail/move`, and `POST /mail/archive` expose explicit foreground lifecycle updates for selected `message_ref` values
- `POST /mail/send`, `POST /mail/post`, and `POST /mail/reply` accept the optional canonical-envelope fields `notify_block` (typed sub-model `{"text": str, "placement": "append" | "prepend"}` with text capped at 512 chars; auto-extracted from a ` ```houmao-notify ` body fence with `placement="append"` when omitted) and `notify_auth` (currently only `scheme="none"` is accepted at envelope validation; non-`none` schemes return HTTP `422` with the canonical `verifier not yet supported` error). The gateway notifier renders `notify_block.text` into the receiver's wake-up prompt at the requested placement subject to the configured trust posture (`notify_block_render`, `notify_block_auth_mode`, `notify_block_auth_verifier`). See [`docs/reference/gateway/contracts/protocol-and-state.md`](gateway/contracts/protocol-and-state.md#mail-notifier-trust-posture) for the configurable knobs and [`docs/reference/mailbox/contracts/canonical-model.md`](mailbox/contracts/canonical-model.md#notification-prompt-block) for the canonical envelope semantics including the auto-mirror invariant.

Observable availability semantics:

- HTTP `503`: no eligible live gateway is attached, the gateway health check fails, or the managed agent does not expose pair-owned mailbox capability
- HTTP `4xx` from the live gateway is forwarded when the mailbox request shape is invalid or the requested mailbox action is rejected downstream

## Native Headless Lifecycle And Durable Turn Inspection

`POST /houmao/agents/headless/launches` launches a passive-server-managed native headless agent.

The resolved launch request requires:

- `tool`
- `working_directory`
- `agent_def_dir`
- `brain_manifest_path`
- `role_name`

Optional launch fields:

- `agent_name`
- `agent_id`
- `headless_display_style`
- `headless_display_detail`
- `mailbox`

`headless_display_style` defaults to `plain` and `headless_display_detail` defaults to `concise` for managed headless sessions. These controls affect live bridge rendering and later CLI replay semantics; they do not change the raw provider artifacts.

Launch-time gateway flags are intentionally not part of this contract. Gateway attach and detach remain same-host scoped `houmao-mgr agents single/self ... gateway ...` actions.

For managed headless agents, durable post-turn inspection stays on the `/turns/*` family:

- `POST /houmao/agents/{agent_ref}/turns` accepts one managed headless prompt turn and returns a durable turn handle; it now also accepts optional `chat_session` with `mode = "auto" | "new" | "current" | "tool_last_or_new" | "exact"` and `id` required only for `mode = "exact"`. Note: `auto` and `current` are gateway-level selectors (`GatewayChatSessionSelectorMode`) resolved by the gateway before dispatch; the internal headless turn API accepts only `new`, `tool_last_or_new`, and `exact`
- `POST /houmao/agents/{agent_ref}/turns` also accepts optional request-scoped `execution.model.name` plus optional `execution.model.reasoning.level` (`>=0`, interpreted against the resolved tool/model ladder). The override is applied only to the submitted turn and does not persist as agent state.
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}` reports persisted turn status
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` returns canonical semantic headless event records with normalized assistant, action, completion, provider, and session semantics
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout` and `/stderr` expose the durable raw provider artifacts directly

Managed headless execution writes artifacts under `<session-root>/<manifest-stem>.turn-artifacts/<turn-id>/`, using the turn ID returned by submission. Turn status, events, and usage recovery read that same manifest-owned directory. The passive server keeps authority and turn-index records under its own runtime root.

`/history` remains bounded and coarse even for headless agents. Durable headless detail lives on `/turns/*`, not on `/history`.

## Finalized Usage Accounting

`GET /houmao/agents/{agent_ref}/usage` exposes finalized usage through one maintained route for both server-managed headless agents and gateway-attached agents. It accepts `after`, an opaque stream cursor, and `limit`, between 1 and 500 with a default of 100.

The passive server selects the authoritative source before querying:

1. A matching persisted server-managed headless authority selects its runtime-session usage ledger. Reading finalized history works without a live controller or attached gateway.
2. Other resolved agents use the live gateway's `GET /v1/usage`. The passive server forwards pagination and preserves the gateway's record IDs, stream identity, capability, collection health, cursor, and continuation state. It does not ingest that agent's provider files or create a second accounting history.

A server-managed authority wins when both paths exist. A retained ledger remains addressable when the controlling headless process has gone away; live prompt control still requires a resumable controller.

The page shape is the shared [gateway usage contract](gateway/contracts/protocol-and-state.md#get-v1usage). Each immutable record identifies its runtime session, generation, managed or native-observed turn, provider identity, final outcome, and available token/cost/timing measurements. Missing measurements remain explicitly unavailable. Qualified TUI usage uses structured native evidence, while unsupported or session-only sources return explicit capability limitations.

Clients keep both the stream identity and the cursor between polls. A simple polling loop follows this sequence:

```text
after = saved_cursor_or_none
page = GET /houmao/agents/{agent_ref}/usage?limit=100[&after=after]
for each previously unseen record_id in page.records:
    consume its available measurements with their scope and inclusion semantics
persist consumed record_ids and page.next_cursor together
after = page.next_cursor
if page.has_more:
    fetch the next page immediately
else:
    wait until the next poll, keeping after even when page.records is empty
```

Commit consumer progress together with processed record identities so retrying a response does not count a turn twice. `has_more = false` identifies the current end, not the end of the stream's lifetime. Older turns that finalize late enter at a new later position. Provider-chat resets preserve the runtime-session stream; a new stream rejects the old cursor rather than silently replaying a different history.

Resolution returns 404 for unknown agents and 409 for ambiguous references. A non-server-managed agent needs an attached reachable gateway; missing or unreachable gateways return 502. Upstream pagination validation returns 422, and incompatible or unreadable usage storage returns 503. Unavailable accounting and degraded collection remain normal capability responses when finalized storage is readable.

See [Usage Records](run-phase/usage-records.md) for metric provenance, deduplication, partial outcomes, source qualification, and accounting limitations.

## CLI Reference

The managed-agent API routes are also reachable through the `houmao-mgr` CLI:

- [scoped agents gateway](cli/agents-gateway.md) — gateway lifecycle and explicit live-gateway request commands
- [scoped agents turn](cli/agents-turn.md) — managed headless turn submission and inspection
- [scoped agents mail](cli/agents-mail.md) — managed-agent mailbox follow-up commands

Scoped `houmao-mgr agents single/self ... prompt` shares the transport-neutral `/requests` surface and accepts the same headless-only request-scoped `--model` plus optional `--reasoning-level` overrides.

## Source References

- [`src/houmao/passive_server/app.py`](../../src/houmao/passive_server/app.py)
- [`src/houmao/passive_server/client.py`](../../src/houmao/passive_server/client.py)
- [`src/houmao/passive_server/models.py`](../../src/houmao/passive_server/models.py)
- [`src/houmao/passive_server/service.py`](../../src/houmao/passive_server/service.py)
- [`src/houmao/server/models.py`](../../src/houmao/server/models.py)
- [`tests/unit/passive_server/test_app_contracts.py`](../../tests/unit/passive_server/test_app_contracts.py)
- [`tests/unit/passive_server/test_service.py`](../../tests/unit/passive_server/test_service.py)
