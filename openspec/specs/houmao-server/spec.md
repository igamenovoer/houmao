## Purpose
Define the public `houmao-server` contract as the Houmao-owned CAO-compatible HTTP authority and its additive extension routes over the native compatibility control core.

## Requirements

### Requirement: `houmao-server` serves `/cao/*` through a Houmao-owned control core
`houmao-server` SHALL satisfy the supported `/cao/*` compatibility surface through the Houmao-owned CAO-compatible control core rather than by proxying to a separate child `cao-server`.

`houmao-server` current-instance, health, and install behavior MAY expose Houmao-owned control-core status, but they SHALL NOT require or publish child-CAO process identity as part of the supported public contract.

In v1, `houmao-server` MAY preserve the existing `/cao/*` route-handler seam through a server-local compatibility transport that projects control-core results back into the current route surface.

#### Scenario: Compatibility routes resolve locally inside `houmao-server`
- **WHEN** a caller uses a supported `/cao/*` route against `houmao-server`
- **THEN** the server dispatches that route into its local control core
- **AND THEN** the caller does not need a hidden child listener for the route to succeed

#### Scenario: Root health omits child-CAO process metadata after absorption
- **WHEN** a caller queries `GET /health` or `GET /houmao/server/current-instance` on a running `houmao-server`
- **THEN** those routes report Houmao-owned server state and any Houmao-owned control-core status that the server chooses to expose
- **AND THEN** they do not require a `child_cao` process record to describe the supported server state

#### Scenario: Root health keeps pair compatibility identity fields
- **WHEN** a pair-owned client queries `GET /health` on a running `houmao-server`
- **THEN** the response still includes `service="cli-agent-orchestrator"` and `houmao_service="houmao-server"`
- **AND THEN** child-CAO-specific metadata is absent

### Requirement: `houmao-server` keeps root and `/houmao/*` namespaces Houmao-owned
`houmao-server` SHALL reserve the server root and the `/houmao/*` route family for Houmao-owned pair behavior.

CAO compatibility SHALL live only under the explicit `/cao/*` route family.

`houmao-server` SHALL NOT expose root-level CAO-compatible session or terminal routes such as `/sessions/*` or `/terminals/*` as part of the supported public contract.

The root `GET /health` route SHALL remain a Houmao-owned pair-health route rather than a CAO-compatible route. CAO-compatible health SHALL be exposed through `/cao/health`.

#### Scenario: Root CAO session route is not part of the supported public contract
- **WHEN** a caller looks for the CAO-compatible session list surface on `houmao-server`
- **THEN** the supported compatibility route is `GET /cao/sessions`
- **AND THEN** `houmao-server` does not expose `GET /sessions` as a supported CAO-compatible route

#### Scenario: Root health remains Houmao-owned while CAO health is namespaced
- **WHEN** a caller needs Houmao pair health from `houmao-server`
- **THEN** the caller uses `GET /health`
- **AND THEN** a caller that needs the CAO-compatible health route uses `GET /cao/health`

### Requirement: `houmao-server` matches the full supported `cao-server` HTTP API
The system SHALL provide a first-party HTTP service named `houmao-server`.

`houmao-server` SHALL expose an HTTP API that is fully compatible with the public HTTP API of the supported `cao-server` version under an explicit `/cao` compatibility namespace.

For the supported `cao-server` version pinned by this change, every public `cao-server` HTTP endpoint SHALL have a corresponding `houmao-server` behavior under `/cao` that preserves the CAO route shape beneath that prefix, methods, request argument names, request-body semantics, response status codes, and response bodies closely enough that work that succeeds against `cao-server` also succeeds against `houmao-server` through `/cao`.

The following routes are explicitly called out because current Houmao usage already depends on them, but compatibility SHALL NOT be limited to this subset:

- `GET /cao/health`
- `GET /cao/sessions`
- `POST /cao/sessions`
- `DELETE /cao/sessions/{session_name}`
- `GET /cao/sessions/{session_name}/terminals`
- `POST /cao/sessions/{session_name}/terminals`
- `GET /cao/terminals/{terminal_id}`
- `GET /cao/terminals/{terminal_id}/working-directory`
- `POST /cao/terminals/{terminal_id}/input`
- `GET /cao/terminals/{terminal_id}/output`
- `POST /cao/terminals/{terminal_id}/exit`
- `DELETE /cao/terminals/{terminal_id}`
- `POST /cao/terminals/{terminal_id}/inbox/messages`
- `GET /cao/terminals/{terminal_id}/inbox/messages`

#### Scenario: Any supported `cao-server` endpoint continues to work through `/cao`
- **WHEN** a caller uses any public HTTP endpoint supported by the pinned `cao-server` version against `houmao-server` through the `/cao` namespace
- **THEN** `houmao-server` accepts the same call pattern with CAO-compatible semantics
- **AND THEN** work that succeeds against `cao-server` also succeeds against `houmao-server` without requiring root-route compatibility aliases

#### Scenario: Namespaced CAO health remains available for compatibility callers
- **WHEN** a caller queries `GET /cao/health` on a running `houmao-server`
- **THEN** the server returns a CAO-compatible health payload for the compatibility surface
- **AND THEN** the caller does not need the root `GET /health` route to preserve CAO semantics

### Requirement: `houmao-server` compatibility is pinned to one exact CAO source of truth
For this capability, the CAO HTTP compatibility source of truth SHALL be pinned to:

- repository: `https://github.com/imsight-forks/cli-agent-orchestrator.git`
- commit: `0fb3e5196570586593736a21262996ca622f53b6`
- local tracked checkout: `extern/tracked/cli-agent-orchestrator`

The system SHALL treat that exact source as the parity oracle for `houmao-server` API compatibility rather than a floating branch name or whichever `cao-server` happens to be on `PATH`.

#### Scenario: HTTP parity verification uses the pinned CAO source
- **WHEN** implementation or verification compares `houmao-server` behavior to CAO behavior
- **THEN** it uses the pinned CAO source of truth for this capability
- **AND THEN** the parity target does not drift with a floating upstream branch

### Requirement: `houmao-server` compatibility is defined within the supported Houmao pair
The compatibility contract for `houmao-server` SHALL be defined as part of the supported `houmao-server + houmao-srv-ctrl` replacement pair for `cao-server + cao`.

This capability SHALL NOT require `houmao-server` to support arbitrary external `cao` clients as a public compatibility contract.

Mixed-pair usage such as `houmao-server + cao` SHALL be treated as unsupported in this capability.

#### Scenario: Mixed server-plus-raw-CAO usage is not part of the compatibility promise
- **WHEN** an operator points a raw `cao` client at `houmao-server`
- **THEN** that combination is outside the supported compatibility contract for this capability
- **AND THEN** parity verification for the capability does not need to claim that mixed pair works

### Requirement: Houmao extensions on CAO-compatible routes are additive only
When `houmao-server` extends an existing CAO-compatible route under `/cao/*`, those extensions SHALL be additive only.

Additive extensions MAY include:

- additional optional request arguments or body fields
- additional optional response fields
- additional new endpoints outside the CAO-compatible route set

`houmao-server` SHALL NOT require Houmao-only arguments or fields in order for a CAO-compatible request under `/cao/*` to succeed, and it SHALL NOT remove or repurpose CAO-defined fields or behaviors on those compatibility routes.

This additive-only restriction SHALL apply to the `/cao/*` compatibility surface. It SHALL NOT require Houmao-owned root routes or `/houmao/*` routes to preserve CAO route shape or CAO naming.

#### Scenario: CAO-compatible callers ignore additive fields on `/cao` safely
- **WHEN** `houmao-server` returns a CAO-compatible response body from a `/cao/*` route with additional Houmao-owned optional fields
- **THEN** a CAO-compatible client that only reads CAO-defined fields still succeeds
- **AND THEN** the additive fields do not break the compatibility contract

#### Scenario: Houmao-owned root routes are not constrained to CAO route shape
- **WHEN** `houmao-server` exposes a Houmao-owned root route or `/houmao/*` route
- **THEN** that route may use Houmao-defined semantics without preserving CAO route names or payload shape
- **AND THEN** the additive-only CAO rule remains scoped to `/cao/*`

### Requirement: Pair-owned `houmao-server` clients keep persisted authority at the server root
When pair-owned Houmao code persists or exchanges `houmao-server` connection state for runtime resume, gateway attach, demos, or query helpers, that persisted authority SHALL remain the public `houmao-server` root base URL rather than a `/cao`-qualified compatibility URL.

The explicit `/cao/*` namespace SHALL be applied through one shared pair-owned compatibility client seam rather than by storing caller-specific compatibility-prefixed base URLs in manifests, attach metadata, or other pair-owned persisted state.

Pair-owned code that needs CAO-compatible session or terminal behavior against `houmao-server` SHALL consume that shared compatibility client seam instead of reconstructing plain root-path `CaoRestClient` instances from persisted `api_base_url` values.

#### Scenario: Runtime resume keeps persisted server authority rooted at the public base URL
- **WHEN** Houmao runtime state persists `houmao-server` connection metadata for a resumable `houmao_server_rest` session
- **THEN** the persisted `api_base_url` remains the public `houmao-server` root authority
- **AND THEN** resumed CAO-compatible session control derives `/cao/*` behavior through the shared compatibility client seam rather than by persisting a `/cao`-qualified URL

#### Scenario: Gateway attach and demos share the same `/cao` client seam
- **WHEN** gateway attach code or a repo-owned demo reconstructs a pair-owned client from persisted or configured `houmao-server` state
- **THEN** that caller uses the same shared compatibility client seam for CAO-compatible session or terminal routes
- **AND THEN** the caller does not invent its own root-path or persisted `/cao` rewrite logic

### Requirement: `houmao-server` separates direct watch observation from CAO-compatible control delegation
`houmao-server` SHALL keep its live watch and parsing path separate from its CAO-compatible control authority.

For live TUI parsing and continuous state tracking, `houmao-server` SHALL observe tmux and process state directly.

For CAO-compatible create, mutate, or control routes, `houmao-server` SHALL use its Houmao-owned control core through the explicit upstream-adapter boundary.

Those control operations SHALL NOT become the authoritative parser or live-state source for watched sessions.

#### Scenario: Local control authority does not replace watch authority
- **WHEN** `houmao-server` creates a session, delivers input, or exits a terminal through the Houmao-owned control core
- **THEN** that control action does not make the control core the authoritative parser or live-state reducer for the watched session
- **AND THEN** the watch plane continues to use direct tmux and process observation

### Requirement: `houmao-server` seeds known-session tracking from server-owned registrations
`houmao-server` SHALL rebuild and refresh the known-session registry for this capability from server-managed session registration records for the sessions this server owns.

It SHALL enrich those registration records with manifest-backed metadata and live tmux facts when available.

Shared live-agent registry records MAY be consulted as compatibility evidence or alias enrichment, but they SHALL NOT by themselves become the primary authority that admits a session into background watch management.

#### Scenario: Startup rebuild uses server-owned registration and live tmux
- **WHEN** `houmao-server` restarts and finds a server-managed registration record whose tmux session is still live
- **THEN** it rebuilds the known-session entry from that registration
- **AND THEN** the resulting background watch worker resumes from that rebuilt entry instead of waiting for child-CAO polling

#### Scenario: Shared registry evidence alone does not create a watched session
- **WHEN** a shared live-agent registry record exists without a matching authoritative server registration record or a verifiable live tmux target
- **THEN** `houmao-server` does not admit that session into its primary known-session registry from the shared registry alone
- **AND THEN** shared registry remains compatibility evidence rather than the watch authority

### Requirement: `houmao-server` owns persistent background watch workers for live terminals
For known tmux-backed Houmao sessions and their live terminals that require Houmao-owned watch behavior, `houmao-server` SHALL run persistent background watch workers independent of whether a caller is currently waiting on one request.

Those watch workers SHALL continuously:

- reconcile against the server's known-session registry,
- inspect tmux session and pane state directly,
- inspect the pane process tree to determine whether the supported TUI is up or down,
- capture pane text directly from tmux when a supported TUI process is running, and
- derive Houmao-owned live state without routing parsing or state tracking through the child `cao-server`.

When the tmux session remains alive but the supported TUI process is down, the watch worker SHALL remain active and SHALL record that condition in the tracked state rather than terminating.

The server SHALL stop or release a watch worker only when the tmux session disappears, the tracked session is no longer known to the server, or the server shuts down.

#### Scenario: Terminal watch continues while no client request is active
- **WHEN** a known tmux-backed live session remains alive and no caller is currently polling or waiting on a request
- **THEN** the corresponding `houmao-server` watch worker continues observing that session in the background
- **AND THEN** the latest Houmao-owned live state remains fresh without requiring a new prompt submission or state query

#### Scenario: TUI-down state does not stop the watch worker
- **WHEN** a watched tmux session still exists but the supported TUI process inside that tmux container is down
- **THEN** `houmao-server` keeps the watch worker active for that session
- **AND THEN** the tracked state records the TUI-down condition instead of treating the session as no longer watchable

#### Scenario: Watch worker lifecycle follows tmux lifecycle
- **WHEN** a watched tmux session disappears or the tracked session is removed from the server's known-session registry
- **THEN** the server stops or releases the corresponding watch worker
- **AND THEN** it does not leave a detached background watcher running for that no-longer-live session

### Requirement: `houmao-server` classifies persistence into filesystem-authoritative, transitional compatibility, and memory-primary state
`houmao-server` SHALL distinguish between durable filesystem-authoritative artifacts that remain canonical on disk, transitional compatibility artifacts that remain filesystem-backed in v1 but are intended to move behind server-owned query APIs later, and live control-plane state that becomes server-owned memory.

At minimum, the filesystem-authoritative bucket SHALL include:

- runtime home roots and runtime manifests,
- durable session roots and session manifests,
- mailbox storage,
- workspace-local job directories,
- server-managed session registration bridges,
- Houmao-owned server roots,
- logs, and
- Houmao-managed compatibility profile-store artifacts.

At minimum, the transitional compatibility bucket SHALL include shared registry live-agent records for v1 and any persisted compatibility-only inbox queue artifacts if the implementation chooses to store them.

At minimum, the memory-primary bucket SHALL include:

- the known-session registry,
- live request and terminal/session registries,
- watch-worker bindings,
- latest parsed TUI state,
- bounded recent transitions or recent-state history,
- current live control-plane views, and
- control-core live bookkeeping.

`houmao-server` SHALL NOT require per-terminal watch snapshot files or append-only watch logs as part of the authoritative live TUI tracking contract.

#### Scenario: Live TUI tracking state exists only in memory
- **WHEN** `houmao-server` updates live parsed TUI state for a watched session
- **THEN** the authoritative truth for that live tracking state exists in server memory
- **AND THEN** the server does not need a persisted watch snapshot file or append-only watch log to treat that state as authoritative

#### Scenario: Shared registry remains on disk without becoming live TUI truth
- **WHEN** `houmao-server` keeps using shared registry records as a v1 compatibility bridge
- **THEN** those registry files may remain on disk
- **AND THEN** they do not become the authoritative source of live tracked TUI state

#### Scenario: Compatibility profile state stays behind Houmao-owned storage
- **WHEN** `houmao-server` needs stored compatibility profiles to create or bootstrap a terminal
- **THEN** it reads those profiles from Houmao-owned server storage
- **AND THEN** callers do not manage a separate CAO-home contract as part of the supported public surface

### Requirement: Tracked-state routes expose simplified turn and last-turn semantics
When `houmao-server` returns server-owned tracked-state payloads for watched sessions, it SHALL expose the simplified turn model as the primary consumer-facing route contract.

At minimum, the tracked-state response SHALL include:

- low-level diagnostics and parsed-surface evidence for the current sample,
- foundational observables under `surface`,
- current turn posture under `turn`, and
- the most recent terminal result under `last_turn`.

For `last_turn`, the route SHALL identify whether the result came from an explicit server-owned input path, inferred direct interaction, or no completed turn yet.

The route SHALL NOT require callers to interpret public turn-anchor states, completion authority states, or completion debounce states in order to understand what the terminal is doing now or what the last turn did.

The route SHALL NOT imply that every visible TUI change has a known cause. If the watched surface changes for unexplained reasons and does not satisfy the server's stricter turn-evidence rules, the route MAY reflect diagnostic or surface churn without manufacturing a new `turn` transition or `last_turn`.

Ambiguous menus, selection boxes, permission prompts, slash-command UI, and similar tool-specific interactive surfaces SHALL be folded into `turn.phase=unknown` unless stronger active or terminal evidence is present. The route SHALL NOT publish a dedicated public ask-user outcome for those surfaces.

The route SHALL NOT publish a generic catch-all failure outcome. Only specifically recognized failure signatures MAY produce `last_turn.result=known_failure`; failure-like but unmatched surfaces SHALL degrade to `turn.phase=unknown` unless stronger evidence supports another state.

The route SHALL NOT distinguish chat turns from slash commands in the public tracked-state contract. Slash-looking input text MAY be reported as surface evidence, but it SHALL NOT create a separate public lifecycle kind.

#### Scenario: Background ready surface exposes a simplified ready turn state
- **WHEN** a caller requests tracked state for a watched terminal whose TUI is idle and visibly ready for another submit
- **THEN** `houmao-server` returns `surface` and `turn` fields that identify a ready turn posture
- **AND THEN** the caller can understand that state without reading public readiness/completion/authority fields

#### Scenario: Explicit server input produces a terminal outcome with explicit source
- **WHEN** `houmao-server` accepts a terminal input submission for a tracked session and that turn later settles successfully
- **THEN** a later tracked-state response records `last_turn.result=success`
- **AND THEN** the response records `last_turn.source=explicit_input`

#### Scenario: Direct tmux prompting can still produce an inferred terminal outcome
- **WHEN** a watched session is prompted directly through tmux instead of the supported server input route
- **AND WHEN** the server safely infers the start and end of that turn from live observation
- **THEN** a later tracked-state response may record the terminal result for that turn
- **AND THEN** the response records `last_turn.source=surface_inference` rather than requiring the caller to inspect turn-anchor internals

#### Scenario: Unexplained surface churn does not manufacture an inferred outcome
- **WHEN** a watched session shows visible surface changes whose cause is not safely attributable to a tracked turn
- **AND WHEN** those changes do not satisfy the server's turn-start or turn-terminal inference rules
- **THEN** the tracked-state response does not manufacture a new `last_turn`
- **AND THEN** the response does not claim a new `turn.phase=active` from that churn alone

### Requirement: `houmao-server` publishes Houmao-owned terminal state and history as explicit extension routes
`houmao-server` SHALL expose Houmao-specific HTTP extension routes for live terminal state and bounded recent transition history in addition to the CAO-compatible core API.

In v1, those live-state and recent-history routes SHALL remain terminal-keyed compatibility routes, and `houmao-server` SHALL resolve `terminal_id` lookups through a compatibility alias map to its Houmao-owned internal tracked-session identity.

Those extension routes SHALL keep Houmao-owned features explicit rather than using breaking changes on CAO-compatible payloads.

At minimum, the Houmao-owned live terminal state contract SHALL distinguish:

- tmux transport state,
- TUI process state,
- parse status,
- optional probe or parse error detail,
- the latest parsed TUI surface when available,
- diagnostic availability or health for the current sample,
- foundational observables under `surface`,
- current turn posture under `turn`,
- the most recent terminal result under `last_turn`,
- generic stability metadata as diagnostic evidence, and
- bounded recent transition or recent-state history when requested.

Those extension routes SHALL be backed by in-memory live state rather than persisted watch files. If recent history is exposed, it SHALL be a bounded in-memory view rather than an append-only persisted log.

#### Scenario: Terminal-keyed route resolves through a compatibility alias
- **WHEN** a caller requests Houmao-owned live state by `terminal_id`
- **THEN** `houmao-server` resolves that lookup through the terminal compatibility alias bound to its internal tracked-session identity
- **AND THEN** the internal known-session registry does not need to be keyed primarily by `terminal_id`

#### Scenario: Callers can inspect Houmao-owned terminal state without scraping raw output
- **WHEN** a caller needs the latest Houmao-owned live state for a watched terminal
- **THEN** the caller can query a dedicated `houmao-server` extension route for that state
- **AND THEN** the caller does not need to reconstruct that state by scraping raw terminal output alone

#### Scenario: Parser or probe failure stays explicit on the extension route
- **WHEN** a watched terminal reaches the extension route with a probe failure or parse failure in the latest cycle
- **THEN** the returned live state distinguishes that failure from a normal TUI-down or successfully parsed cycle
- **AND THEN** the route does not fabricate a parsed surface for that failed cycle

#### Scenario: Recent transitions are exposed from memory rather than persisted watch logs
- **WHEN** a watched terminal has experienced multiple recent observed state changes during the current server lifetime
- **THEN** `houmao-server` may expose those recent transitions through its extension routes
- **AND THEN** that recent-history view is served from bounded in-memory state rather than from append-only persisted watch logs

#### Scenario: Restart rebuilds live state instead of replaying stale watch files
- **WHEN** `houmao-server` restarts and resumes watching still-live known sessions
- **THEN** it rebuilds the extension-route live state from fresh observation of those sessions
- **AND THEN** it does not treat old watch snapshot files or old append-only watch logs as the authoritative rebuilt state

### Requirement: `houmao-server` keeps TUI registration separate from native headless launch
`houmao-server` SHALL keep its existing server-owned registration bridge for terminal-backed compatibility sessions and SHALL NOT require that bridge for native headless agents.

For TUI-backed registrations, `terminal_id` SHALL remain part of the compatibility registration contract.

For headless agents, `houmao-server` SHALL create server authority through its Houmao-owned native headless launch path instead of through delegated registration.

#### Scenario: TUI registration remains terminal-keyed
- **WHEN** a caller registers a TUI-backed managed session through the compatibility registration bridge
- **THEN** `houmao-server` continues to require `terminal_id` for that registration
- **AND THEN** the TUI registration path remains distinct from the native headless launch path

#### Scenario: Headless authority does not require delegated registration
- **WHEN** a caller launches a headless managed agent through the native headless API
- **THEN** `houmao-server` creates authority for that agent without requiring a delegated launch registration record
- **AND THEN** headless lifecycle does not depend on child-CAO session or terminal discovery

### Requirement: `houmao-server` persists native headless authority under the server-owned state tree
For each native headless agent launched through `houmao-server`, the server SHALL persist a dedicated managed-agent authority record under the server-owned state tree.

In v1, that authority subtree SHALL live under:

```text
<server_root>/state/managed_agents/<tracked_agent_id>/
```

That subtree SHALL contain an `authority.json` record for the launched headless agent.

At minimum, that `authority.json` record SHALL persist:

- `tracked_agent_id`
- `tool`
- `manifest_path`
- `session_root`
- `tmux_session_name`
- optional `agent_name`
- optional `agent_id`

`houmao-server` SHALL use that authority record plus runtime-owned evidence such as the manifest and session root to rebuild headless agent authority on startup or recovery.

`houmao-server` SHALL NOT admit a headless agent from a stray manifest alone when no matching server-owned headless authority record exists.

#### Scenario: Native headless launch writes server-owned authority
- **WHEN** `houmao-server` successfully launches a native headless agent
- **THEN** it writes an `authority.json` record under `state/managed_agents/<tracked_agent_id>/`
- **AND THEN** later restart recovery can use that server-owned authority record to rebuild the managed agent

#### Scenario: Stray manifest without authority is not re-admitted
- **WHEN** a runtime manifest for a headless session still exists on disk
- **AND WHEN** no matching server-owned `authority.json` record exists for that headless session
- **THEN** `houmao-server` does not re-admit that headless session into managed-agent authority from the manifest alone
- **AND THEN** restart recovery remains bounded by explicit server-owned authority

### Requirement: `houmao-server` persists active headless turn authority and reconciles it across restart
When `houmao-server` accepts a headless turn for a managed headless agent, it SHALL persist active-turn authority under the same managed-agent authority subtree.

In v1, that active-turn record SHALL live at:

```text
<server_root>/state/managed_agents/<tracked_agent_id>/active_turn.json
```

At minimum, `active_turn.json` SHALL persist:

- `tracked_agent_id`
- `turn_id`
- `turn_index`
- `turn_artifact_dir`
- `started_at_utc`
- live targeting metadata needed for later interrupt or reconciliation when available

Single-active-turn admission gating and active-turn interrupt targeting SHALL use that persisted active-turn authority rather than depending only on in-memory runner state.

On startup or recovery, `houmao-server` SHALL reconcile `active_turn.json` against live tmux evidence and durable turn artifacts before it admits another turn for that agent or reports that the agent has no active turn.

If reconciliation determines the earlier turn is still active, `houmao-server` SHALL restore active-turn authority for that turn.

If reconciliation determines the earlier turn has already reached a terminal state, `houmao-server` SHALL clear the active-turn record and reopen turn admission for that agent.

#### Scenario: Restart preserves single-active-turn gating for a live turn
- **WHEN** `houmao-server` restarts while `active_turn.json` exists for a headless managed agent
- **AND WHEN** reconciliation determines that recorded turn is still active
- **THEN** the server continues rejecting overlapping turn submissions for that agent
- **AND THEN** single-active-turn semantics do not disappear merely because the server restarted

#### Scenario: Restart clears active-turn authority for a terminal turn
- **WHEN** `houmao-server` restarts while `active_turn.json` exists for a headless managed agent
- **AND WHEN** reconciliation determines that recorded turn has already reached a terminal state
- **THEN** the server clears the active-turn record
- **AND THEN** the next turn submission for that agent may be admitted normally

### Requirement: `houmao-server` maintains a managed-agent registry that includes headless agents
In addition to the existing known-session tracking for terminal-backed sessions, `houmao-server` SHALL maintain a server-owned managed-agent registry that can represent both TUI-backed and headless agents.

For TUI-backed agents, that managed-agent registry MAY project from the existing known-session registry and terminal-alias mappings.

For headless agents, that managed-agent registry SHALL use server-owned `authority.json`, reconciled `active_turn.json`, runtime-owned manifest state, and turn-artifact evidence to maintain live identity and coarse state, and SHALL NOT require a fabricated terminal alias.

On startup or recovery, `houmao-server` SHALL rebuild server-launched headless managed agents from server-owned headless authority plus manifest-backed runtime evidence rather than requiring child CAO session discovery.

#### Scenario: Headless managed agent rebuilds after server restart
- **WHEN** `houmao-server` restarts and finds a valid server-owned headless launch record whose manifest and session root still exist
- **THEN** it rebuilds that headless managed agent into the managed-agent registry
- **AND THEN** the headless agent becomes available again through `/houmao/agents/*` without needing a `terminal_id`

#### Scenario: Headless admission does not fabricate a terminal alias
- **WHEN** `houmao-server` admits a registered headless managed agent
- **THEN** it tracks that agent through managed-agent identity plus headless metadata
- **AND THEN** it does not invent a fake `terminal_id` solely to fit the headless agent into terminal-keyed structures

### Requirement: Existing CAO-compatible and terminal-keyed routes remain TUI-specific compatibility surfaces
When `houmao-server` adds headless managed-agent support, it SHALL keep existing CAO-compatible `/cao/sessions/*` and `/cao/terminals/*` routes plus existing `/houmao/terminals/{terminal_id}/*` routes as TUI-specific or CAO-compatible surfaces.

`houmao-server` SHALL NOT publish registered headless managed agents as fake CAO sessions or fake terminals on those routes.

Headless managed agents SHALL instead be exposed through the Houmao-owned `/houmao/agents/*` route family.

#### Scenario: Headless managed agent stays off terminal-keyed compatibility routes
- **WHEN** `houmao-server` is managing a registered headless Claude agent
- **THEN** that headless agent is available through `/houmao/agents/*`
- **AND THEN** the server does not fabricate a terminal-keyed compatibility entry for it on `/houmao/terminals/{terminal_id}/*`

#### Scenario: TUI compatibility routes remain available for terminal-backed sessions
- **WHEN** `houmao-server` is managing a TUI-backed session that already has a `terminal_id`
- **THEN** callers can continue using `/cao/sessions/*`, `/cao/terminals/*`, and the existing terminal-keyed compatibility routes for that session
- **AND THEN** adding headless managed-agent support does not remove or rename the TUI compatibility surface outside the explicit `/cao` namespace move

### Requirement: `houmao-server` keeps registration bridge storage contained under the server-owned sessions root
When `houmao-server` persists or removes server-owned registration records for tracked sessions, it SHALL treat the registration storage key as a validated server-owned identifier rather than as a raw filesystem path fragment.

`houmao-server` SHALL reject registration or deletion inputs whose session identifier cannot be represented safely inside the configured `sessions/` root.

`houmao-server` SHALL verify that the resolved registration path remains under the configured `sessions/` root before writing or removing any registration directory.

#### Scenario: Invalid registration identifier is rejected before write
- **WHEN** a caller sends a registration request whose session identifier would escape or otherwise violate the server-owned `sessions/` storage namespace
- **THEN** `houmao-server` rejects that request before creating or modifying any registration directory
- **AND THEN** the server does not write a registration file outside the configured `sessions/` root

#### Scenario: Registration cleanup remains root-contained
- **WHEN** `houmao-server` removes a server-owned registration record during session or terminal cleanup
- **THEN** it resolves the cleanup target within the same validated server-owned `sessions/` namespace
- **AND THEN** the server does not remove directories outside the configured `sessions/` root

### Requirement: `houmao-server` keeps background tracking resilient across unexpected runtime failures
`houmao-server` SHALL keep the tracking supervisor and per-session watch workers resilient against unexpected runtime exceptions.

Unexpected reconcile failures SHALL NOT permanently terminate the supervisor thread for the lifetime of the server process.

Unexpected session-poll failures SHALL NOT permanently terminate the corresponding watch worker unless the tracked session has actually left live authority.

When such failures affect live-state observation, `houmao-server` SHALL surface an explicit error state for that session or otherwise record the failure for operator diagnosis rather than silently ceasing background tracking.

#### Scenario: Reconcile failure does not permanently stop the supervisor
- **WHEN** one reconcile pass raises an unexpected runtime exception while loading or reconciling live known sessions
- **THEN** `houmao-server` records or logs that failure and keeps the supervisor available for later reconcile passes
- **AND THEN** continuous background tracking can resume without restarting the server process

#### Scenario: Session poll failure does not permanently stop the worker
- **WHEN** one watch-worker cycle raises an unexpected runtime exception while polling a still-live tracked session
- **THEN** `houmao-server` records an explicit failure for that session and keeps the worker eligible to poll again on a later cycle
- **AND THEN** one bad poll does not permanently disable live tracking for that session

### Requirement: `houmao-server` removes live-state aliases when a tracked session leaves live authority
The terminal-keyed Houmao live-state routes SHALL resolve only through terminal aliases that remain bound to a currently live known session.

When a tracked session leaves the live known-session registry, loses tmux liveness, or is otherwise released from background watch authority, `houmao-server` SHALL evict the corresponding in-memory worker binding, tracker state, and terminal alias from its live authority maps.

#### Scenario: Tmux loss removes stale live-state authority
- **WHEN** a watched tracked session loses tmux liveness and a later reconcile pass no longer admits that session into the live known-session registry
- **THEN** `houmao-server` removes the corresponding in-memory tracker and terminal alias from live authority
- **AND THEN** terminal-keyed live-state lookup no longer succeeds only from stale in-memory residue

#### Scenario: Registry removal releases the live terminal alias
- **WHEN** a tracked session is removed from the authoritative known-session registry even if an older in-memory tracker still exists
- **THEN** `houmao-server` evicts the existing terminal alias and tracker from the live route authority
- **AND THEN** the live-state routes reflect that the session is no longer known to the server

### Requirement: `houmao-server` preserves tracked pane identity during registration-seeded admission
When `houmao-server` admits a tracked session from its registration bridge, it SHALL preserve available tmux pane-targeting metadata needed to select the intended tracked pane on the first live polling cycles.

That registration-seeded identity SHALL include tmux window metadata when the caller provides it, and `houmao-server` SHALL enrich the identity from manifest-backed metadata during admission when a manifest path is available and the registration payload omits that metadata.

The initial tracker state SHALL use that preserved or enriched pane identity rather than falling back blindly to whichever tmux pane is active for the session.

#### Scenario: Registration-supplied window metadata is used immediately
- **WHEN** a registration request includes tmux window identity for the tracked session
- **THEN** `houmao-server` persists and applies that window identity when creating the initial tracked-session record
- **AND THEN** the first live polling cycles target that registered window instead of choosing an arbitrary active pane

#### Scenario: Manifest-backed window metadata enriches the initial tracker
- **WHEN** a registration request omits tmux window identity but supplies a manifest path whose metadata identifies the tracked tmux window
- **THEN** `houmao-server` enriches the initial tracked-session record from that manifest before the first live polling cycles
- **AND THEN** registration-seeded tracking does not need to wait for a later reconcile pass to recover the correct pane target

### Requirement: `houmao-server` uses replaceable upstream adapters and v1 SHALL support a native CAO-compatible engine
`houmao-server` SHALL interact with underlying live terminal providers through an explicit upstream-adapter boundary rather than embedding one backend's control logic into the public server contract.

That upstream-adapter boundary SHALL support at minimum:

- session creation and deletion
- terminal creation and deletion
- terminal metadata lookup
- terminal output retrieval
- prompt or control input delivery
- interrupt or exit delivery
- upstream health or connectivity checks

In v1 after this change, the system SHALL provide a Houmao-owned native CAO-compatible engine behind that boundary, composed from a tmux controller, provider adapters, a profile store, and CAO compatibility projection layers.

That v1 engine SHALL preserve the current pair compatibility launch provider identifiers accepted by the supported pair surface:

- `kiro_cli`
- `claude_code`
- `codex`
- `gemini_cli`
- `kimi_cli`
- `q_cli`

The public `houmao-server` API SHALL remain Houmao-owned even when the implementation continues to compare itself to CAO as a parity oracle.

#### Scenario: V1 server serves terminal lifecycle from the native control core
- **WHEN** a caller creates a terminal through `houmao-server` in the supported pair
- **THEN** `houmao-server` may use its Houmao-owned CAO-compatible engine to create the underlying terminal
- **AND THEN** the caller still interacts with `houmao-server` as the public session authority

#### Scenario: Compatibility-core degradation does not make root health unreadable
- **WHEN** the native compatibility control core becomes degraded while `houmao-server` is still running
- **THEN** `GET /health` on `houmao-server` still reports server-local liveness
- **AND THEN** Houmao-owned terminal state reflects upstream or provider degradation separately from server process health

### Requirement: `houmao-server` is designed to outgrow CAO rather than permanently mirror it
The system SHALL treat CAO compatibility as a migration strategy, not as the final architecture of `houmao-server`.

The Houmao-owned watch state, persistence, and extension routes SHALL NOT depend on CAO-specific protocol details beyond what the current upstream adapter needs internally.

Future native Houmao-owned terminal backends SHALL be able to replace the CAO-backed adapter without requiring a second public rename away from `houmao-server`.

#### Scenario: Replacing the upstream adapter does not require changing the public server name
- **WHEN** a future implementation replaces the CAO-backed adapter with a native Houmao-owned backend
- **THEN** the public server remains `houmao-server`
- **AND THEN** callers do not need to switch back to CAO-branded service identities to keep using the server

### Requirement: `houmao-server` compatibility SHALL be verified against a real `cao-server`
The implementation SHALL include verification that uses the pinned `cao-server` source to exercise the CAO-compatible HTTP routes exposed under `/cao/*` and the Houmao-owned server behavior that sits around those routes.

Because `houmao-server` no longer proxies those routes to a child CAO process in the supported runtime path, verification SHALL focus on behavioral parity between the Houmao-owned implementation and the pinned CAO oracle rather than on passthrough wiring alone.

That compatibility verification SHALL cover at minimum:

- `/cao/*` endpoint availability and routing
- path-segment encoding and routing
- request argument, query, and request-body handling
- required-versus-optional input handling
- additive-extension safety on `/cao/*` compatibility routes
- compatibility inbox behavior where those routes remain exposed

Houmao-owned behavior SHALL be tested directly and more strictly. That verification SHALL cover at minimum:

- root `/health` pair-health behavior
- current-instance persistence and reporting
- launch registration behavior
- terminal state and history route correctness
- watch-worker lifecycle and runtime-owned state reduction
- install behavior against the Houmao-owned profile store
- migration-failure behavior for deprecated standalone CAO surfaces

#### Scenario: `/cao` parity verification catches request-surface regressions
- **WHEN** a `houmao-server` compatibility route under `/cao/*` changes in a way that breaks CAO-compatible path, query, or body handling
- **THEN** parity verification against the pinned `cao-server` detects the divergence
- **AND THEN** the implementation can reject that change before claiming compatibility-safe behavior

#### Scenario: Houmao-owned verification catches root or native-route regressions
- **WHEN** a Houmao-owned root route or `/houmao/*` route changes in a way that breaks server-owned behavior
- **THEN** direct Houmao behavior verification detects the regression
- **AND THEN** the implementation can reject that change even though `/cao/*` parity may still succeed

### Requirement: `houmao-server` exposes a pair-owned install surface for compatibility profile state
`houmao-server` SHALL expose a Houmao-owned install surface that lets paired clients install compatibility profiles into the server-managed Houmao profile store without direct access to internal storage layout details.

That install surface SHALL accept the install inputs needed by the supported pair, including the provider plus agent source or profile reference needed for the install operation.

The server-owned install path SHALL absorb the minimum used CAO install behavior required by the pair, including source resolution, required profile validation/frontmatter handling, provider-specific materialization, and profile metadata indexing behind server-owned storage.

`houmao-server` SHALL resolve compatibility profile-store paths internally. The public contract SHALL NOT require callers to provide or compute CAO-home-like paths or hidden control-core storage locations.

#### Scenario: Pair client installs profile through the public server authority
- **WHEN** a paired client submits a profile-install request to `houmao-server` for provider `codex`
- **THEN** `houmao-server` performs that install against its Houmao-managed compatibility profile store
- **AND THEN** the caller does not need to inspect or mutate hidden profile-store filesystem layout directly

#### Scenario: Failed pair-owned install returns an explicit server-owned error
- **WHEN** the underlying install operation fails while `houmao-server` is handling a pair-owned install request
- **THEN** `houmao-server` returns an explicit failure through the public Houmao surface
- **AND THEN** the caller does not need to infer failure indirectly from missing files under internal compatibility storage

### Requirement: Session detail responses preserve terminal summary metadata needed by pair clients
For the CAO-compatible `GET /cao/sessions/{session_name}` route, `houmao-server` SHALL preserve the session-detail structure and terminal-summary metadata exposed by the supported CAO source closely enough that paired Houmao clients can consume that response as a typed contract.

At minimum, the session-detail response SHALL let a pair client identify the created terminal id together with the tmux session and tmux window metadata carried by the supported CAO session summary.

#### Scenario: Session detail exposes terminal window metadata for paired clients
- **WHEN** a caller queries `GET /cao/sessions/{session_name}` through `houmao-server` for a live session whose terminal summary includes tmux window metadata in the supported CAO source
- **THEN** the `houmao-server` response preserves that terminal summary metadata on the compatibility route
- **AND THEN** paired Houmao clients can persist that tmux window identity into registration or runtime artifacts without scraping unrelated routes

#### Scenario: Session detail remains compatible for callers that ignore extra terminal summary fields
- **WHEN** a CAO-compatible caller reads the `GET /cao/sessions/{session_name}` response but ignores terminal summary fields it does not use
- **THEN** the compatibility response still succeeds as a valid session-detail view
- **AND THEN** preserving tmux session or window metadata does not force callers onto a separate Houmao-only route just to use the pair
