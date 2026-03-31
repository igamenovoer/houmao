# agent-gateway Specification

## Purpose
Define the durable per-agent gateway companion, including its storage layout, HTTP surface, execution policy, and recovery behavior.
## Requirements
### Requirement: Per-agent gateway companion introduces no visible operator surface by default and may attach after session start
The system SHALL support a per-agent gateway companion for gateway-capable tmux-backed sessions.

Outside pair-managed same-session `houmao_server_rest` topology and outside explicit foreground attach mode, the gateway companion SHALL NOT require or create a separate visible tmux window or pane for normal operation.

For pair-managed same-session `houmao_server_rest` sessions and for runtime-owned tmux-backed sessions whose attach flow explicitly requests foreground mode, the gateway companion MAY run in an auxiliary tmux window in the same tmux session so long as that auxiliary window does not redefine the contractual managed-agent surface.

The gateway companion MAY be started immediately after a managed session starts or later by attaching to an already-running tmux-backed session.

The gateway companion SHALL direct its own logs away from the contractual operator-facing agent surface. When foreground mode is active, gateway console output SHALL appear only in the auxiliary gateway window and gateway-owned durable log storage, not on the agent surface in tmux window `0`.

#### Scenario: Attach-later preserves a single visible TUI surface by default
- **WHEN** a gateway companion attaches to an already-running tmux-backed session without explicit foreground mode outside the supported pair-managed same-session `houmao_server_rest` topology
- **THEN** the managed agent TUI remains the only visible operator surface for normal interaction
- **AND THEN** the attach flow does not require creating a visible tmux pane or window for the gateway

#### Scenario: Runtime-owned foreground attach may add an auxiliary window
- **WHEN** a gateway companion attaches to an already-running runtime-owned tmux-backed session with explicit foreground mode enabled
- **THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion
- **AND THEN** that auxiliary window does not become the contractual managed-agent surface

#### Scenario: Pair-managed same-session gateway does not redefine the contractual agent surface
- **WHEN** a pair-managed `houmao_server_rest` gateway companion runs in an auxiliary tmux window in the same tmux session
- **THEN** that auxiliary window does not become the contractual managed-agent surface
- **AND THEN** the primary agent surface remains distinct from the gateway window

#### Scenario: Gateway logging does not paint onto the shared terminal
- **WHEN** the gateway companion emits logs or diagnostics during normal operation
- **THEN** that output is written to gateway-owned log storage rather than the contractual operator-facing tmux surface
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing TUI surface

### Requirement: Pair-owned gateway attach for managed `houmao_server_rest` sessions supports explicit and current-session targeting
When called through the current-session contract, the command SHALL require execution inside the target agent's tmux session, SHALL discover the current tmux session as the attach context, SHALL prefer `HOUMAO_MANIFEST_PATH` from that tmux session when present and valid, and SHALL otherwise use `HOUMAO_AGENT_ID` from that same tmux session to resolve exactly one fresh shared-registry record and `runtime.manifest_path`.

Current-session attach SHALL NOT fall back to retired `AGENTSYS_*` names. It SHALL also NOT fall back to `HOUMAO_GATEWAY_ATTACH_PATH`, `HOUMAO_GATEWAY_ROOT`, `terminal_id`, cwd, ambient shell env, or another server target when manifest or shared-registry discovery is invalid or stale.

#### Scenario: Current-session attach prefers HOUMAO manifest pointer
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from the owning tmux session
- **AND WHEN** that tmux session publishes a valid `HOUMAO_MANIFEST_PATH`
- **THEN** the attach flow resolves authority from that manifest pointer

#### Scenario: Current-session attach falls back to HOUMAO agent id through the shared registry
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from a tmux session whose `HOUMAO_MANIFEST_PATH` is unusable
- **AND WHEN** the tmux session publishes `HOUMAO_AGENT_ID`
- **THEN** the attach flow resolves authority through exactly one fresh shared-registry record

### Requirement: Pair-managed `houmao_server_rest` gateway companions may run in an auxiliary tmux window without redefining the agent surface
For pair-managed tmux-backed `houmao_server_rest` sessions, the system SHALL allow the gateway companion to run in a separate auxiliary tmux window in the same tmux session for normal operation.

When the gateway companion runs in the same tmux session, the system SHALL keep tmux window `0` reserved for the managed agent surface and SHALL keep gateway output off that primary agent window.

When the gateway companion runs in the same tmux session, the runtime SHALL treat the gateway auxiliary tmux window and pane as the authoritative local execution surface for gateway lifecycle management. It SHALL use tmux-owned pane state for local liveness, SHALL use gateway health responses for readiness, and SHALL target that auxiliary tmux surface for shutdown rather than relying on a detached subprocess handle.

The gateway companion SHALL continue writing its own durable logs to gateway-owned storage even when its console output is visible in an auxiliary tmux window.

The `houmao-server` process and its internal child-CAO support state SHALL remain outside the agent's tmux session even when the gateway companion runs in the same managed session as the agent.

#### Scenario: Attach-later adds an auxiliary window without redefining the agent surface
- **WHEN** a gateway companion attaches later to an already-running pair-managed `houmao_server_rest` session
- **THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion
- **AND THEN** tmux window `0` remains the canonical managed agent surface for that session

#### Scenario: Gateway logging stays off the primary agent surface
- **WHEN** the gateway companion emits logs or diagnostics while running in an auxiliary tmux window
- **THEN** the gateway output appears only in the auxiliary process window and gateway-owned durable log storage
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing agent window `0`

#### Scenario: Same-session gateway lifecycle uses the auxiliary tmux surface
- **WHEN** the gateway companion runs in an auxiliary tmux window for a pair-managed `houmao_server_rest` session
- **THEN** the runtime determines local gateway liveness from the auxiliary tmux pane state for that window
- **AND THEN** the runtime waits for successful gateway health responses before treating the gateway as ready
- **AND THEN** shutdown and crash cleanup target the auxiliary tmux gateway surface rather than a detached subprocess handle

### Requirement: Runtime-owned foreground gateway companions may run in an auxiliary tmux window without redefining the agent surface
For runtime-owned tmux-backed managed sessions launched through `houmao-mgr`, the system SHALL allow the gateway companion to run in a separate auxiliary tmux window in the same tmux session when foreground mode is explicitly requested.

When that foreground mode is active, the system SHALL keep tmux window `0` reserved for the managed agent surface and SHALL keep gateway output off that primary agent window.

When that foreground mode is active, the runtime SHALL treat the gateway auxiliary tmux window and pane as the authoritative local execution surface for gateway lifecycle management. It SHALL use tmux-owned pane state for local liveness, SHALL use gateway health responses for readiness, and SHALL target that auxiliary tmux surface for shutdown rather than relying on a detached subprocess handle.

The gateway companion SHALL continue writing its own durable logs to gateway-owned storage even when its console output is visible in an auxiliary tmux window.

#### Scenario: Runtime-owned foreground attach adds an auxiliary window without redefining the agent surface
- **WHEN** a gateway companion attaches later to an already-running runtime-owned tmux-backed session with explicit foreground mode enabled
- **THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion
- **AND THEN** tmux window `0` remains the canonical managed agent surface for that session
- **AND THEN** the gateway auxiliary window uses a tmux window index `>=1`

#### Scenario: Runtime-owned foreground gateway logging stays off the primary agent surface
- **WHEN** the gateway companion emits logs or diagnostics while running in an auxiliary tmux window for a runtime-owned session
- **THEN** the gateway output appears only in the auxiliary gateway window and gateway-owned durable log storage
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing agent window `0`

#### Scenario: Runtime-owned foreground gateway lifecycle uses the auxiliary tmux surface
- **WHEN** the gateway companion runs in an auxiliary tmux window for a runtime-owned tmux-backed session
- **THEN** the runtime determines local gateway liveness from the auxiliary tmux pane state for that window
- **AND THEN** the runtime waits for successful gateway health responses before treating the gateway as ready
- **AND THEN** shutdown and crash cleanup target the auxiliary tmux gateway surface rather than a detached subprocess handle

### Requirement: Same-session gateway live state persists an authoritative execution handle
The runtime SHALL persist one authoritative live gateway record under `<session-root>/gateway/run/current-instance.json`.

When the gateway runs in a same-session auxiliary tmux window, that live record SHALL include an explicit execution mode plus the tmux window and pane identifiers for the auxiliary gateway surface, in addition to the listener and managed-agent instance fields needed for live gateway status.

Detach, crash cleanup, and auxiliary-window recreation SHALL resolve the live gateway surface from that runtime-owned record rather than from ad hoc tmux discovery over non-contractual auxiliary windows.

When auxiliary-window recreation replaces the live gateway surface, the runtime SHALL update the authoritative live gateway record before treating the recreated gateway as ready.

When the same-session auxiliary-window mode is active, the recorded tmux window index SHALL NOT be `0`.

#### Scenario: Same-session live gateway record captures the tmux execution handle
- **WHEN** a gateway companion starts in an auxiliary tmux window
- **THEN** the runtime persists one live gateway record under `<session-root>/gateway/run/current-instance.json`
- **AND THEN** that record identifies the same-session execution mode plus the auxiliary tmux window and pane identifiers for the live gateway surface

#### Scenario: Auxiliary-window recreation updates the authoritative live gateway record
- **WHEN** a same-session gateway auxiliary window is replaced during detach, cleanup, or recovery
- **THEN** the runtime updates the authoritative live gateway record to the new tmux window and pane identifiers
- **AND THEN** later detach or cleanup targets the recreated auxiliary gateway surface without rediscovering non-contractual windows heuristically

### Requirement: The gateway maintains a durable per-agent control root
Each gateway-capable session SHALL have a deterministic per-agent gateway root under the runtime-owned storage hierarchy once attachability is published or a gateway first attaches.

For runtime-owned sessions in v1, the canonical runtime-owned session root SHALL be `<runtime_root>/sessions/<backend>/<session_id>/`, using the runtime-generated session id used for session-manifest storage, and the gateway root SHALL be the nested `gateway/` subdirectory under that session root.

That gateway root SHALL contain at minimum:

- a protocol-version marker
- a read-optimized current state artifact
- a durable queued-request store
- an append-only event log

The gateway SHALL recover pending work and the latest persisted status from that gateway root when the gateway companion process restarts and the managed session still exists.

The current gateway state artifact SHALL be a stable, protocol-versioned local read contract, SHALL use the same schema as `GET /v1/status`, and SHALL be written atomically.

For gateway-capable sessions with no currently running gateway instance, the current gateway state artifact SHALL still exist and SHALL represent an offline or not-attached gateway condition rather than disappearing.

The gateway root SHALL distinguish stable attachability metadata from live gateway-instance metadata.

#### Scenario: Gateway restart recovers queued work from durable state
- **WHEN** the gateway companion process exits unexpectedly while its managed tmux session remains available
- **AND WHEN** durable queued requests exist in the gateway root
- **THEN** a restarted gateway companion recovers those queued requests from durable storage
- **AND THEN** the gateway does not require callers to resubmit already accepted pending work solely because the sidecar process restarted

#### Scenario: External readers can inspect the latest gateway state without replaying the event log
- **WHEN** an operator or local tool needs the latest gateway status for a managed session
- **THEN** the system provides that status through the current gateway state artifact in the gateway root
- **AND THEN** the caller does not need to reconstruct current state solely by replaying the append-only event log

#### Scenario: First attach creates gateway-owned durable state for a running session
- **WHEN** a gateway companion first attaches to a running tmux-backed session that previously had no gateway process
- **THEN** the system creates or materializes the gateway root for that session
- **AND THEN** the initial gateway state is seeded from current observation plus attach metadata rather than requiring pre-attach event history

#### Scenario: Gateway-capable session exposes offline state before first attach
- **WHEN** a runtime-owned tmux-backed session has published gateway capability but no gateway instance has ever attached yet
- **THEN** the gateway root already contains the current gateway state artifact for that session
- **AND THEN** that state artifact reports an offline or not-attached gateway condition

#### Scenario: Runtime-owned gateway root is nested under the session root
- **WHEN** the runtime provisions gateway capability for runtime-owned session `cao_rest-20260312-120000Z-abcd1234`
- **THEN** the runtime-owned session root for that session is `<runtime_root>/sessions/<backend>/<session_id>/`
- **AND THEN** the gateway root for that session is `<session-root>/gateway`
- **AND THEN** gateway-owned durable state stays colocated with the agent session rather than in a separate top-level gateway tree

### Requirement: Stable attachability metadata is distinct from live gateway bindings
The system SHALL publish stable attachability metadata for gateway-capable sessions independently from whether a gateway process is currently running.

Stable attachability metadata SHALL be sufficient for a later attach flow to determine how to attach to the live session through `manifest.json` together with tmux-local discovery and shared-registry fallback. `gateway_manifest.json` MAY exist as derived outward-facing gateway bookkeeping, but SHALL NOT be the authoritative input for attach resolution.

Live gateway bindings such as active host, port, and state-path pointers SHALL describe only the currently running gateway instance and SHALL be treated as ephemeral.

The manifest SHALL remain the durable stable authority for the session and SHALL NOT persist live gateway host, port, or state-path values.

For tmux-backed sessions, the runtime SHALL also expose a runtime-owned discovery path that resolves the current live gateway bindings without requiring callers to infer localhost defaults.

For same-session discovery inside the managed tmux session, that discovery path SHALL:

- prefer complete valid live gateway bindings already present in the current process env,
- fall back to the owning tmux session's live gateway publication when the current process env lacks the required live gateway values,
- validate the resolved live binding against manifest-backed session authority and live gateway health before returning it.

For cross-session or out-of-process discovery, that discovery path SHALL:

- use tmux-local manifest discovery when available,
- otherwise use the shared registry to recover `runtime.manifest_path`,
- derive the session root from that manifest path,
- treat `<session-root>/gateway/run/current-instance.json` as the authoritative local live-gateway record for that session,
- use shared-registry gateway connect metadata only as locator metadata rather than as the sole authoritative live-gateway record.

That runtime-owned discovery path SHALL surface at minimum the current `host`, `port`, `base_url`, `protocol_version`, and `state_path` for the attached gateway instance and SHALL report gateway unavailability explicitly when no valid live gateway binding exists.

#### Scenario: Gateway-capable session exists with no running gateway
- **WHEN** a tmux-backed session has published attach metadata but no gateway companion is currently running
- **THEN** the session remains gateway-capable
- **AND THEN** callers can distinguish that state from one where a live gateway instance is currently attached

#### Scenario: Live gateway bindings are cleared on graceful stop
- **WHEN** an attached gateway companion stops gracefully while the managed tmux session remains live
- **THEN** the system preserves stable attachability metadata for later re-attach
- **AND THEN** live gateway host or port bindings are removed or invalidated for that stopped instance

#### Scenario: Current-session attach does not trust `gateway_manifest.json` as stable authority
- **WHEN** a current-session attach flow resolves a valid manifest through tmux-local discovery or shared-registry fallback
- **THEN** it uses that manifest as the stable attach authority
- **AND THEN** any existing `gateway_manifest.json` is treated as derived publication rather than as the authoritative input

#### Scenario: Runtime-owned helper resolves live gateway bindings from manifest-backed authority
- **WHEN** a tmux-backed session has a live attached gateway and a valid runtime-owned manifest path
- **THEN** the runtime-owned gateway discovery path resolves the live endpoint from that session's current validated live gateway publication
- **AND THEN** the returned payload includes the exact current `host`, `port`, `base_url`, `protocol_version`, and `state_path`
- **AND THEN** the caller does not need to enumerate raw tmux env or infer localhost defaults

#### Scenario: Same-session discovery falls back from process env to the owning tmux session env
- **WHEN** work is running inside the managed tmux session
- **AND WHEN** the current process env does not contain a complete valid live gateway binding
- **AND WHEN** the owning tmux session env does contain the current live gateway binding
- **THEN** the runtime-owned discovery path resolves the live endpoint from that owning tmux session env
- **AND THEN** it validates that resolved binding before returning it

#### Scenario: Cross-session discovery uses the shared registry to recover the manifest locator
- **WHEN** a caller needs live gateway discovery outside the managed session
- **AND WHEN** tmux-local manifest discovery is unavailable
- **AND WHEN** the shared registry has a fresh record for that session with `runtime.manifest_path`
- **THEN** the runtime uses that manifest path to locate the runtime-owned session
- **AND THEN** it treats the session-owned `gateway/run/current-instance.json` record as the authoritative local live-gateway record
- **AND THEN** any registry-published gateway connect metadata remains locator metadata rather than the sole authority

#### Scenario: Runtime-owned helper reports gateway unavailable when no valid live binding exists
- **WHEN** a tmux-backed session is gateway-capable but no attached gateway instance is currently valid
- **THEN** the runtime-owned gateway discovery path reports gateway unavailability explicitly
- **AND THEN** the caller does not guess another host or port from stale process env or localhost heuristics

#### Scenario: Current-session attach does not trust `gateway_manifest.json` as stable authority
- **WHEN** a current-session attach flow resolves a valid manifest through tmux-local discovery or shared-registry fallback
- **THEN** it uses that manifest as the stable attach authority
- **AND THEN** any existing `gateway_manifest.json` is treated as derived publication rather than as the authoritative input

### Requirement: Native headless gateway attach supports tmux current-session targeting without requiring a live worker process
For native headless tmux-backed sessions, the system SHALL allow gateway attach from inside the owning tmux session using manifest-first discovery from `HOUMAO_MANIFEST_PATH` or `HOUMAO_AGENT_ID`.

#### Scenario: Native headless attach accepts HOUMAO current-session discovery
- **WHEN** a developer runs gateway attach from inside the owning native headless tmux session
- **AND WHEN** that session publishes a valid `HOUMAO_MANIFEST_PATH`
- **THEN** the system resolves the target from `HOUMAO_MANIFEST_PATH`

### Requirement: Gateway bootstrap artifacts are internal runtime state rather than supported public authority
Gateway bootstrap artifacts SHALL remain internal runtime state rather than supported public authority.

The system MAY keep internal gateway bootstrap artifacts such as `attach.json` under the session-owned gateway root when runtime or server internals still need them for startup seeding, offline status materialization, or managed-agent metadata transfer.

Those artifacts SHALL be treated as internal runtime state rather than supported public authority for attach or control behavior.

External attach, resume, relaunch, and control flows SHALL use manifest-backed authority plus shared-registry and tmux-local discovery rather than reading `attach.json` or another bootstrap artifact directly as the contract.

`gateway_manifest.json` SHALL remain outward-facing bookkeeping only. When internal bootstrap artifacts and manifest-backed authority disagree, manifest-backed authority wins for supported behavior.

#### Scenario: Internal bootstrap artifacts may still exist after migration
- **WHEN** runtime or server internals still need bootstrap metadata to seed gateway startup or offline status
- **THEN** the session-owned gateway root may contain `attach.json` or equivalent internal bootstrap files
- **AND THEN** those files are not part of the supported external attach contract

#### Scenario: Supported attach does not read internal bootstrap files as authority
- **WHEN** an external attach or control flow targets a managed session after the manifest-first migration
- **THEN** it resolves authority from `manifest.json` plus tmux-local or shared-registry discovery
- **AND THEN** it does not require `attach.json` to exist or remain authoritative

### Requirement: Gateway-managed recovery uses the tmux-backed relaunch contract rather than build-time launch
For tmux-backed sessions that a gateway attaches to, the resolved manifest SHALL be sufficient for later gateway-managed agent relaunch without rebuilding the brain home.

When the attached session uses tmux-local relaunch authority, the gateway SHALL use the shared runtime relaunch primitive backed by `manifest.json` plus the owning tmux session env.

Gateway-managed relaunch SHALL NOT route through build-time `houmao-mgr agents launch`, SHALL NOT require per-agent launcher directories in shared registry, and SHALL NOT depend on copied launcher scripts or copied credentials outside the owning tmux session.

Gateway-managed relaunch SHALL always target tmux window `0` for the managed agent surface and SHALL NOT allocate a new tmux window.

#### Scenario: Gateway relaunch reuses the existing built home
- **WHEN** an attached gateway requests relaunch for a tmux-backed managed session
- **THEN** the gateway uses manifest-owned relaunch posture plus the current tmux session env
- **AND THEN** it does not rebuild the brain home

#### Scenario: Gateway relaunch does not search for another tmux window
- **WHEN** an attached gateway relaunches the managed agent surface for a tmux-backed session
- **THEN** it targets window `0`
- **AND THEN** it does not allocate a replacement window when the user has repurposed that window

### Requirement: Each running gateway instance binds one resolved host and port
Each running gateway instance SHALL expose its gateway submit or status surface as an HTTP service bound on exactly one resolved listener address before that gateway instance starts accepting work.

Allowed listener hosts in this change are exactly `127.0.0.1` and `0.0.0.0`.

When no explicit all-interface bind host is configured, the gateway companion SHALL default to binding on `127.0.0.1:<resolved-port>`.

The gateway companion SHALL attempt to bind that resolved port during startup and SHALL NOT silently switch to a different port if binding fails.

When no explicit gateway port is configured, the system SHALL request a system-assigned port during gateway bind and SHALL NOT pre-probe a free port in the parent runtime process.

When the resolved port is unavailable because another process already owns it or because the bind otherwise fails, startup of that gateway instance SHALL fail explicitly.

When a gateway instance starts successfully with a system-assigned port, the system SHALL persist that resolved host and port as the desired listener for that gateway root and SHALL reuse them on later restarts unless explicitly overridden.

#### Scenario: Gateway starts on the default loopback listener
- **WHEN** the system starts a gateway companion for a gateway-capable tmux-backed session with resolved gateway port `43123`
- **AND WHEN** no explicit all-interface bind host is configured
- **THEN** the gateway companion binds an HTTP service on `127.0.0.1:43123`
- **AND THEN** live gateway discovery for that instance reflects port `43123` rather than an unrelated substituted port

#### Scenario: Explicit all-interface bind uses 0.0.0.0
- **WHEN** the system starts a gateway companion with resolved gateway host `0.0.0.0` and port `43123`
- **THEN** the gateway companion binds an HTTP service on `0.0.0.0:43123`
- **AND THEN** the service is reachable through any host interface address that maps to that port

#### Scenario: Port conflict fails gateway attach or start
- **WHEN** the system attempts to start a gateway companion whose resolved gateway port is already bound by another process
- **THEN** the system fails that gateway start or attach operation with an explicit gateway-port conflict error
- **AND THEN** it does not silently retry on a different port for that launch attempt

#### Scenario: Successful system-assigned listener is reused on restart
- **WHEN** a gateway companion first starts successfully with a system-assigned port
- **THEN** the system records that resolved host and port as the desired listener for the gateway root
- **AND THEN** a later restart of that same gateway root reuses that listener unless a caller explicitly overrides it

### Requirement: Gateway supports ephemeral one-off and repeating wakeup jobs
The live gateway SHALL expose dedicated wakeup routes for direct timer registration without requiring mailbox participation.

That wakeup surface SHALL include:

- `POST /v1/wakeups`
- `GET /v1/wakeups`
- `GET /v1/wakeups/{job_id}`
- `DELETE /v1/wakeups/{job_id}`

Each wakeup job SHALL include a predefined prompt and SHALL use either:

- one-off mode with exactly one requested due time, or
- repeating mode with an interval and next due time.

The gateway SHALL keep registered wakeup jobs entirely in the live gateway process memory. Pending wakeup jobs and due-but-not-yet-executed wakeup occurrences SHALL NOT survive gateway shutdown or restart.

Deleting a wakeup job SHALL cancel that job while it remains scheduled. Deleting a repeating wakeup job SHALL stop future repetitions. If execution of one wakeup occurrence has already started, deleting the job SHALL NOT retroactively retract that already-started prompt execution.

Unknown `job_id` lookups or cancellations SHALL fail explicitly rather than pretending the wakeup still exists.

#### Scenario: Caller registers one one-off wakeup
- **WHEN** a caller submits `POST /v1/wakeups` with a predefined prompt and one one-off due time
- **THEN** the live gateway returns a wakeup job identifier for that scheduled wakeup
- **AND THEN** the new wakeup is visible through `GET /v1/wakeups` and `GET /v1/wakeups/{job_id}` while it remains scheduled

#### Scenario: Caller registers one repeating wakeup
- **WHEN** a caller submits `POST /v1/wakeups` with mode `repeat`, a predefined prompt, and a repeat interval
- **THEN** the live gateway schedules a repeating wakeup for that job
- **AND THEN** later inspection shows that the job remains registered until it is canceled or the gateway stops

#### Scenario: Gateway restart drops pending wakeups
- **WHEN** the live gateway stops or restarts while one or more wakeup jobs are still scheduled
- **THEN** those pending wakeup jobs are lost
- **AND THEN** the restarted gateway does not recover them from gateway persistence artifacts

#### Scenario: Canceling a repeating wakeup stops future occurrences
- **WHEN** a caller deletes a repeating wakeup job that is still registered
- **THEN** the live gateway cancels that wakeup job explicitly
- **AND THEN** no later repeating occurrences are scheduled for that deleted job

### Requirement: Due wakeups remain gateway-owned low-priority internal prompt delivery
When a wakeup becomes due, the gateway SHALL treat delivery of that wakeup prompt as gateway-owned internal execution behavior rather than as a new externally visible public request kind.

The public terminal-mutating request-kind set SHALL remain limited to `submit_prompt` and `interrupt`.

Before a due wakeup prompt starts execution, the gateway SHALL require:

- request admission to be open,
- no active terminal-mutating execution,
- zero durable public queue depth.

If those conditions are not satisfied when a wakeup becomes due, the gateway SHALL keep that wakeup pending in memory and SHALL retry later instead of dropping the reminder or converting it into durable queued work.

Repeating wakeups SHALL maintain at most one pending due occurrence per job. Missed intervals during a busy period SHALL NOT produce a catch-up burst of multiple immediate prompt deliveries once the gateway becomes idle again.

#### Scenario: Busy gateway defers a due wakeup
- **WHEN** a wakeup becomes due while request admission is blocked, active execution is running, or durable public queue depth is non-zero
- **THEN** the gateway does not start that wakeup prompt immediately
- **AND THEN** the wakeup remains pending in memory until a later safe execution opportunity

#### Scenario: Due wakeup does not expand the public request-kind set
- **WHEN** a wakeup prompt is delivered after becoming due
- **THEN** that delivery happens through gateway-owned internal behavior rather than a new public `POST /v1/requests` kind
- **AND THEN** the public terminal-mutating request kinds remain exactly `submit_prompt` and `interrupt`

#### Scenario: Repeating wakeup does not backfill missed intervals as a burst
- **WHEN** a repeating wakeup remains overdue across multiple interval boundaries because the gateway is busy
- **THEN** the gateway preserves at most one pending overdue occurrence for that repeating job
- **AND THEN** the gateway does not emit one immediate prompt for every missed interval once the gateway becomes idle

### Requirement: The gateway exposes a structured HTTP API on the resolved listener address
The gateway SHALL expose an HTTP API for health inspection, status inspection, gateway-managed request submission, wakeup registration and inspection, gateway-owned notifier control, and, when permitted by mailbox bindings and listener policy, shared mailbox operations on the resolved listener address for that session.

The base gateway HTTP API SHALL expose `GET /health`, `GET /v1/status`, and `POST /v1/requests`.

The wakeup HTTP API SHALL additionally expose `POST /v1/wakeups`, `GET /v1/wakeups`, `GET /v1/wakeups/{job_id}`, and `DELETE /v1/wakeups/{job_id}`.

For mailbox-enabled sessions whose live gateway listener is bound to loopback, that HTTP API SHALL additionally expose `GET /v1/mail/status`, `POST /v1/mail/check`, `POST /v1/mail/send`, `POST /v1/mail/reply`, and `POST /v1/mail/state`.

When the gateway mail notifier capability is implemented, that HTTP API SHALL additionally expose `PUT /v1/mail-notifier`, `GET /v1/mail-notifier`, and `DELETE /v1/mail-notifier`.

`GET /health` SHALL return a structured response suitable for runtime launch-readiness checks and SHALL include gateway protocol-version information.

`GET /health` SHALL reflect gateway-local process and control-plane health, and SHALL NOT fail solely because the managed agent is unavailable, recovering, or awaiting rebind.

`GET /v1/status` SHALL return the same versioned status model that the gateway persists to `state.json`.

`POST /v1/requests` SHALL accept typed request-creation payloads and SHALL return the accepted queued request record.

The wakeup routes SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to mutate gateway memory or private runtime objects directly.

The notifier control endpoints SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write gateway SQLite state directly.

The shared mailbox routes SHALL be limited to mailbox status, `check`, `send`, `reply`, and explicit single-message read-state update behaviors supported by both the filesystem and `stalwart` transports.

Those shared mailbox routes SHALL use structured request and response payloads and SHALL NOT require callers to read or write transport-local SQLite state, filesystem `rules/`, or Stalwart-native objects directly.

That HTTP API SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write SQLite state directly.

Request-validation failures on `POST /v1/requests` SHALL return HTTP `422`. Explicit gateway policy rejection SHALL return HTTP `403`. Request-state conflicts such as reconciliation-required admission blocking SHALL return HTTP `409`. Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

Wakeup-route validation failures SHALL return HTTP `422`. Unknown wakeup identifiers on `GET /v1/wakeups/{job_id}` or `DELETE /v1/wakeups/{job_id}` SHALL return HTTP `404`.

Notifier validation failures SHALL return HTTP `422`. Attempts to enable notifier behavior for sessions that cannot support it SHALL fail explicitly rather than pretending that notifier polling is active.

Shared mailbox route validation failures SHALL return HTTP `422`. Calls to mailbox routes for sessions without mailbox bindings SHALL fail explicitly rather than pretending mailbox support exists. When the live gateway listener is bound to `0.0.0.0`, the `/v1/mail/*` routes SHALL fail explicitly as unavailable until an authentication model exists for broader listeners.

Read-oriented HTTP endpoints and mailbox read routes SHALL NOT consume the terminal-mutation slot solely to report current gateway health, core status, wakeup state, notifier status, or shared mailbox state.

#### Scenario: Health inspection uses default loopback surface
- **WHEN** a tool inspects a gateway-managed session whose resolved gateway host is `127.0.0.1`
- **THEN** it can query `GET /health` through the loopback HTTP surface on the resolved port
- **AND THEN** the gateway returns a structured health response without requiring direct SQLite access

#### Scenario: Gateway health remains readable during upstream recovery
- **WHEN** the gateway companion remains healthy but the managed agent is unavailable, recovering, or awaiting rebind
- **THEN** `GET /health` still returns a structured gateway-local health response for that running gateway instance
- **AND THEN** callers use `GET /v1/status` to inspect managed-agent connectivity, recovery, and admission state

#### Scenario: Status inspection matches the stable state artifact
- **WHEN** a tool queries `GET /v1/status` for a gateway-managed session
- **THEN** the gateway returns the same versioned status model that it persists to `state.json`
- **AND THEN** local readers can rely on either surface without schema drift

#### Scenario: Request submission uses all-interface surface when configured
- **WHEN** a tool submits gateway-managed terminal-mutating work for a session whose resolved gateway host is `0.0.0.0`
- **THEN** it may submit that work through `POST /v1/requests` on any reachable host interface address on the resolved port
- **AND THEN** the gateway validates and records the request before it can compete for execution

#### Scenario: Wakeup registration uses the live gateway HTTP surface
- **WHEN** a caller needs to register or inspect one live wakeup job for an attached gateway-managed session
- **THEN** the caller uses the dedicated `/v1/wakeups` route family on that live gateway listener
- **AND THEN** the caller does not need to mutate private runtime state or transport queue artifacts directly

#### Scenario: Unknown wakeup identifier fails explicitly
- **WHEN** a caller requests `GET /v1/wakeups/{job_id}` or `DELETE /v1/wakeups/{job_id}` for a non-existent wakeup job
- **THEN** the gateway rejects that call explicitly
- **AND THEN** it does not pretend that the requested wakeup still exists

#### Scenario: Filesystem-backed mailbox check uses the dedicated gateway mail surface
- **WHEN** a caller performs mailbox `check` against a mailbox-enabled session whose resolved mailbox transport is `filesystem`
- **THEN** the live gateway serves that operation through `POST /v1/mail/check`
- **AND THEN** the caller receives normalized mailbox message metadata without reading mailbox-local SQLite directly

#### Scenario: Stalwart-backed mailbox reply uses the same dedicated gateway mail surface
- **WHEN** a caller performs mailbox `reply` against a mailbox-enabled session whose resolved mailbox transport is `stalwart`
- **THEN** the live gateway serves that operation through `POST /v1/mail/reply`
- **AND THEN** the caller uses the same shared gateway mailbox contract rather than Stalwart-native transport objects directly

#### Scenario: Session without mailbox binding rejects gateway mailbox routes explicitly
- **WHEN** a caller invokes a gateway mailbox route for a managed session whose manifest has no mailbox binding
- **THEN** the gateway rejects that mailbox route call explicitly
- **AND THEN** it does not claim mailbox support for that session

#### Scenario: Non-loopback gateway listener rejects shared mailbox routes
- **WHEN** a live gateway listener is bound to `0.0.0.0`
- **AND WHEN** a caller invokes one of the shared `/v1/mail/*` routes
- **THEN** the gateway rejects that mailbox route call as unavailable for the current listener configuration
- **AND THEN** terminal-mutating routes remain available under their existing listener rules

#### Scenario: Invalid request payload is rejected with validation semantics
- **WHEN** a caller submits a malformed `POST /v1/requests` payload
- **THEN** the gateway returns HTTP `422`
- **AND THEN** the malformed request is not accepted into durable queue state

#### Scenario: Notifier control surface is available alongside the base gateway API
- **WHEN** a caller needs to enable, inspect, or disable gateway mail notification for a mailbox-enabled session
- **THEN** the gateway exposes the dedicated `/v1/mail-notifier` control routes on the same resolved listener
- **AND THEN** callers do not need to mutate gateway queue persistence directly to manage notifier behavior

### Requirement: Shared gateway mailbox facade supports explicit read-state updates by opaque message reference
For mailbox-enabled sessions whose live gateway listener is bound to loopback, the shared gateway mailbox facade SHALL expose `POST /v1/mail/state` alongside the existing shared mailbox routes.

That shared mailbox state-update route SHALL accept exactly one opaque `message_ref` target and the explicit read-state mutation field it supports in this change.

For this change, the shared mailbox state-update contract SHALL support explicit single-message `read` mutation for one message addressed to the current session principal, callers SHALL express that mutation as `read=true`, and the route SHALL reject broader mailbox-state fields such as `starred`, `archived`, or `deleted`.

The gateway SHALL resolve that request through the same manifest-backed mailbox adapter boundary used by the other `/v1/mail/*` routes rather than by inventing a second transport-local state path inside the gateway service layer.

The shared mailbox state-update route SHALL remain loopback-only under the same listener-availability rules as the rest of the shared `/v1/mail/*` surface.

The shared mailbox state-update route SHALL NOT consume the single terminal-mutation slot used by `POST /v1/requests`.

The shared mailbox state-update route SHALL return a structured acknowledgment of the resulting read state for that `message_ref` rather than a full delivered-message envelope.

Before returning that acknowledgment, the gateway SHALL validate that the normalized transport state evidence used to derive the response includes an explicit boolean read or unread signal, and it SHALL fail explicitly rather than inferring `read=true` from a missing field.

#### Scenario: Filesystem-backed session marks one processed message read through the shared facade
- **WHEN** a caller invokes `POST /v1/mail/state` for a loopback-bound filesystem mailbox session with a valid opaque `message_ref` and `read=true`
- **THEN** the gateway applies that read-state update for the current session principal through the filesystem mailbox adapter
- **AND THEN** the canonical message content remains immutable while recipient-local read state changes

#### Scenario: Stalwart-backed session marks one processed message read through the shared facade
- **WHEN** a caller invokes `POST /v1/mail/state` for a loopback-bound `stalwart` mailbox session with a valid opaque `message_ref` and `read=true`
- **THEN** the gateway applies that read-state update through the Stalwart-backed mailbox adapter
- **AND THEN** the caller does not need to understand transport-owned message identifiers to complete that update

#### Scenario: Malformed transport normalization does not produce an inferred read acknowledgment
- **WHEN** a mailbox adapter returns state-update normalization without an explicit boolean read or unread signal after `POST /v1/mail/state`
- **THEN** the gateway rejects that state update explicitly
- **AND THEN** it does not acknowledge the message as read by inferring success from the missing field

### Requirement: Gateway status separates gateway health, upstream-agent state, recovery, admission, surface eligibility, and execution state
The gateway SHALL publish a structured status model that separates gateway health from managed-agent connectivity, recovery state, request-admission state, and terminal-surface readiness.

That published status model SHALL be protocol-versioned and SHALL be shared by both `state.json` and `GET /v1/status`.

At minimum, the published gateway status SHALL distinguish:

- protocol version
- stable session identity
- current managed-agent instance epoch
- gateway health state
- managed-agent connectivity state
- managed-agent recovery state
- request-admission state
- terminal-surface eligibility state
- active execution state
- gateway execution mode
- gateway host
- gateway port
- queue depth

When the gateway is running in `tmux_auxiliary_window` mode, the published gateway status SHALL additionally expose the authoritative tmux execution handle for that live gateway surface, including the tmux window index and tmux window identifier. It MAY also expose the tmux pane identifier.

When the gateway cannot safely classify the managed terminal surface, it SHALL publish an explicit unknown-like state rather than inferring readiness.

`gateway health state` SHALL support representing that no gateway instance is currently attached to an otherwise gateway-capable session.

`request-admission state` SHALL support representing that the gateway remains alive while terminal-mutating work is paused or rejected because the managed agent is recovering, unavailable, or requires reconciliation after rebinding.

#### Scenario: Managed-agent crash changes upstream status without corrupting gateway health
- **WHEN** the gateway companion remains alive but the managed agent crashes unexpectedly
- **THEN** the published status keeps gateway health separate from the managed-agent connectivity and recovery states
- **AND THEN** the gateway does not claim that the whole control plane is dead solely because the upstream agent failed

#### Scenario: Replacement upstream instance increments the managed-agent epoch
- **WHEN** bounded recovery rebinds the logical session to a replacement managed-agent instance
- **THEN** the published status reflects a new managed-agent instance epoch for that same stable session identity
- **AND THEN** clients can distinguish "same session, new upstream instance" from "same session, same upstream instance"

#### Scenario: Manual modal interaction changes surface eligibility without corrupting gateway health
- **WHEN** a human operator opens or leaves the managed TUI in a non-submit-ready modal surface
- **THEN** the gateway updates the published terminal-surface eligibility state to reflect that non-ready surface
- **AND THEN** the gateway does not mark itself unhealthy solely because the operator changed the TUI surface

#### Scenario: Foreground gateway status exposes the tmux execution handle
- **WHEN** the gateway companion runs in `tmux_auxiliary_window` mode
- **THEN** the published status includes `execution_mode=tmux_auxiliary_window`
- **AND THEN** the published status exposes the authoritative tmux window index and tmux window identifier for that live gateway surface

#### Scenario: Uncertain surface classification stays explicit
- **WHEN** the gateway cannot safely determine whether the managed terminal surface is ready for injection
- **THEN** the gateway publishes an explicit non-ready or unknown-like surface state
- **AND THEN** it does not silently treat the surface as submit-ready

### Requirement: The gateway serializes terminal-mutating work and applies admission policy
The gateway SHALL accept structured local requests for gateway-managed work and SHALL apply gateway-owned admission policy before execution.

In v1, the public terminal-mutating request kinds SHALL be exactly `submit_prompt` and `interrupt`.

Mailbox transport operations SHALL use the dedicated `/v1/mail/*` routes rather than introducing new public terminal-mutating request kinds.

The HTTP submission contract SHALL expose typed per-kind payloads. Any persisted `payload_json` field remains an internal storage detail rather than part of the public protocol contract.

For accepted terminal-mutating requests, the gateway SHALL persist them durably, SHALL serialize execution through a single active terminal-mutation slot per managed agent, and SHALL order eligible work according to gateway policy such as priority, timing constraints, or coalescing rules.

The gateway SHALL be able to reject requests explicitly when permissions or local policy do not allow them.

The gateway SHALL determine terminal-mutating request admission using the published request-admission state rather than only gateway-process liveness.

Already accepted but not-yet-started terminal-mutating work SHALL remain durable while bounded managed-agent recovery is in progress.

If the managed agent fails while a terminal-mutating request is active, the gateway SHALL record an explicit failed or outcome-unknown result for that request and SHALL NOT silently replay it against a replacement managed-agent instance unless the backend adapter has positively established safe continuity.

When managed-agent recovery or reconciliation state makes safe execution impossible, the gateway SHALL reject new terminal-mutating admission explicitly rather than accepting work that it cannot safely apply.

#### Scenario: Prompt submission is accepted as a typed request
- **WHEN** a caller submits a `submit_prompt` request with a prompt-string payload
- **THEN** the gateway validates and durably enqueues that request
- **AND THEN** the accepted response includes a durable request identifier

#### Scenario: Interrupt submission is accepted as a typed request
- **WHEN** a caller submits an `interrupt` request for a gateway-managed session
- **THEN** the gateway records it as a gateway-managed control action
- **AND THEN** the caller does not need to bypass the gateway with direct concurrent terminal mutation

#### Scenario: Mailbox send does not create a new public terminal-mutating request kind
- **WHEN** a caller uses the gateway to perform mailbox `send`
- **THEN** that operation uses the dedicated gateway mailbox surface rather than `POST /v1/requests`
- **AND THEN** the public terminal-mutating request-kind set remains limited to `submit_prompt` and `interrupt`

#### Scenario: Concurrent terminal-mutating requests are serialized
- **WHEN** multiple accepted terminal-mutating requests target the same managed agent concurrently
- **THEN** the gateway allows at most one of those requests to hold the active execution slot at a time
- **AND THEN** later eligible requests remain queued until the active terminal-mutation slot is released

#### Scenario: Disallowed request is rejected before execution
- **WHEN** a submitted gateway request violates configured permission or policy rules
- **THEN** the gateway rejects that request explicitly
- **AND THEN** the rejected request is not executed against the managed terminal surface

#### Scenario: Accepted queued work survives transient upstream outage
- **WHEN** terminal-mutating work has already been accepted durably and the managed agent becomes unavailable before that work begins
- **THEN** the gateway preserves that queued work durably
- **AND THEN** execution remains paused until recovery or reconciliation reopens safe admission

#### Scenario: Active prompt is not replayed blindly after upstream replacement
- **WHEN** a `submit_prompt` request is active and the managed agent fails unexpectedly before the gateway can confirm a terminal outcome
- **AND WHEN** bounded recovery later rebinds the logical session to a replacement managed-agent instance
- **THEN** the gateway records the interrupted request as failed or outcome-unknown
- **AND THEN** the gateway does not silently replay that same prompt against the replacement upstream instance

#### Scenario: New prompt admission is rejected while recovery blocks safe execution
- **WHEN** a caller submits a new `submit_prompt` request while the gateway's request-admission state is paused or closed because the managed agent is unavailable, recovering, or awaiting reconciliation
- **THEN** the gateway rejects that request with explicit unavailable or conflict semantics
- **AND THEN** the gateway does not pretend that queued execution can proceed safely

### Requirement: Gateway-managed operation does not depend on mailbox enablement
The gateway SHALL NOT require mailbox transport configuration, mailbox environment bindings, or mailbox-triggered workflows in order to launch, publish status, accept gateway-managed work, or recover a gateway-managed session.

Future mailbox integration MAY submit work through the same validated gateway request surface in a follow-up change, but this change SHALL NOT make mailbox participation a hidden dependency of gateway operation.

#### Scenario: Gateway-managed session operates without mailbox support
- **WHEN** the system starts or attaches a gateway companion for a tmux-backed session that does not enable any mailbox transport
- **THEN** the gateway companion still launches, publishes gateway state, and accepts gateway-managed work
- **AND THEN** gateway operation does not fail solely because mailbox support is absent

#### Scenario: Missing mailbox bindings do not block gateway recovery
- **WHEN** a gateway-managed session is resumed or recovered without mailbox-specific environment bindings
- **THEN** gateway discovery, status inspection, and recovery continue to rely on gateway-owned state and runtime metadata
- **AND THEN** the system does not require mailbox bindings to continue gateway-managed operation

### Requirement: Direct human TUI interaction is a supported concurrent activity
The gateway SHALL treat direct human interaction with the managed TUI as a supported concurrent activity rather than as protocol corruption.

When human interaction leaves the managed surface in a state that is not safely eligible for gateway injection, the gateway SHALL pause or defer queued terminal-mutating work until eligibility returns.

Direct human interaction SHALL NOT, by itself, invalidate already accepted queued work.

#### Scenario: Human interaction pauses queued injection without discarding queued work
- **WHEN** queued terminal-mutating work exists for a gateway-managed agent
- **AND WHEN** a human operator changes the managed TUI into a non-submit-ready surface before the queued work begins
- **THEN** the gateway defers injection until the surface is safely eligible again
- **AND THEN** the gateway retains the accepted queued work instead of discarding it solely because the human interacted with the TUI

#### Scenario: Human interaction during active work is recorded and reconciled
- **WHEN** a human operator changes the managed TUI while a gateway-owned request is in progress
- **THEN** the gateway records that observation in its state or event history
- **AND THEN** the gateway reevaluates the active request outcome according to its recovery or retry policy instead of assuming the session is irreparably corrupted

### Requirement: The gateway supports timers, heartbeats, bounded local recovery, replacement-instance awareness, and snapshot-based later attach
The gateway SHALL support regular gateway heartbeats, managed-agent liveness observation, timer-driven request creation, and bounded recovery for agent-local failures.

Timer-driven or wakeup-oriented queued work in v1 SHALL remain gateway-owned internal behavior rather than additional externally submitted public request kinds.

When a gateway first attaches to an already-running session, the gateway SHALL initialize from current observation plus attach metadata rather than requiring continuous launch-time observation.

When the managed agent fails or becomes unavailable while the gateway companion remains alive, the gateway SHALL attempt bounded recovery through the runtime-owned backend integration for that session and SHALL record the recovery outcome.

Bounded recovery SHALL distinguish at least:

- reconnecting to the same managed-agent instance
- rebinding the logical session to a replacement managed-agent instance
- exhausting recovery while keeping the gateway alive for inspection and later rebind

When bounded recovery rebinds the logical session to a replacement managed-agent instance, the gateway SHALL preserve the stable session identity, SHALL record a new managed-agent instance epoch, and SHALL require reconciliation before replaying unsafe terminal-mutating work unless the backend adapter can positively establish safe continuity.

If bounded recovery exhausts without restoring safe continuity, the gateway SHALL remain available for `GET /health`, `GET /v1/status`, and local state inspection while publishing a non-open request-admission state.

When the entire tmux session or tmux server hosting the managed agent disappears, the gateway SHALL surface that loss as an offline or degraded condition and SHALL NOT claim full self-recovery of the destroyed tmux container from within the gateway companion itself.

#### Scenario: Agent-local failure triggers bounded gateway recovery
- **WHEN** the gateway remains alive but observes that the managed agent process or terminal surface has failed in a recoverable way
- **THEN** the gateway attempts bounded recovery using the configured backend integration for that managed session
- **AND THEN** the gateway records whether recovery succeeded, retried, or exhausted its retry budget

#### Scenario: Same-instance recovery reopens paused admission
- **WHEN** the gateway pauses admission because the managed agent became temporarily unavailable
- **AND WHEN** bounded recovery reconnects to the same managed-agent instance with safe continuity
- **THEN** the gateway may reopen request admission for that same stable session without changing the managed-agent instance epoch
- **AND THEN** previously paused queued work can resume according to normal scheduling rules

#### Scenario: Replacement-instance recovery requires reconciliation
- **WHEN** bounded recovery succeeds only by rebinding the logical session to a replacement managed-agent instance
- **THEN** the gateway preserves the stable session identity but records a new managed-agent instance epoch
- **AND THEN** the gateway surfaces a reconciliation-required admission state before unsafe automation resumes

#### Scenario: Exhausted recovery keeps the gateway available for inspection
- **WHEN** the gateway exhausts its bounded recovery attempts for a logical session while the gateway process itself remains alive
- **THEN** `GET /health`, `GET /v1/status`, and `state.json` remain available for inspection
- **AND THEN** the gateway publishes an unavailable or awaiting-rebind admission state instead of pretending the whole gateway died

#### Scenario: Whole tmux-session loss is surfaced for outer supervision
- **WHEN** the tmux session hosting the managed TUI is destroyed while a gateway instance had been attached
- **THEN** the gateway contract surfaces that loss as an offline or degraded condition when state is next inspected
- **AND THEN** recovery of the destroyed tmux container is left to an outer launcher or supervisor layer rather than being claimed by the gateway companion alone

### Requirement: Gateway writes a tail-friendly running log to disk
The gateway SHALL maintain a running log on disk under its gateway-owned root so operators can monitor live behavior by tailing one stable file.

That running log SHALL live under the gateway log directory and SHALL be append-only and line-oriented so common file-tail tools can follow it while the gateway is active.

The running log SHALL cover at minimum:

- gateway process start and stop,
- attach and detach outcomes,
- notifier enable, disable, and configuration changes when notifier is supported,
- notifier poll outcomes such as unread detected, busy deferral, and enqueue success when notifier is supported,
- request execution start and terminal outcome,
- explicit gateway-side errors that affect live behavior.

The running log SHALL remain a human-oriented observability surface. Structured artifacts such as `state.json`, `events.jsonl`, and gateway SQLite state remain the authoritative machine-readable contracts for status, history, and recovery.

The gateway SHALL avoid unbounded log spam from high-frequency identical poll outcomes by rate-limiting, coalescing, or periodically summarizing repetitive messages.

#### Scenario: Operator can tail one stable gateway log file
- **WHEN** an operator wants to watch live gateway behavior for one session
- **THEN** the gateway writes append-only log lines to one stable file under the gateway root
- **AND THEN** the operator can follow that file with ordinary tail-style tooling while the gateway is active

#### Scenario: Busy notifier retries are visible without flooding the log
- **WHEN** unread mail exists but the notifier keeps finding the managed agent busy across multiple polling cycles
- **THEN** the gateway running log records that notifier work is being deferred for retry
- **AND THEN** the gateway avoids emitting an unbounded identical busy message on every single short poll forever

### Requirement: Gateway notifier wake-up semantics are unread-set based rather than per-message based
When gateway-owned notifier behavior is enabled for a mailbox-backed session, the gateway SHALL treat notification eligibility as a function of whether unread mail exists for that session and whether the session is eligible to receive a reminder prompt.

If a poll cycle finds multiple unread messages, the gateway MAY enqueue a single internal reminder prompt that summarizes the unread set for that cycle, including message metadata such as titles or identifiers.

The gateway SHALL NOT require one internal reminder prompt per unread message in order to satisfy notifier behavior.

If the unread set has not changed since the last successful reminder and the messages remain unread, the gateway MAY skip emitting a duplicate reminder until the unread set changes or the messages are marked read explicitly.

#### Scenario: Multiple unread messages can be summarized in one reminder prompt
- **WHEN** one notifier poll cycle observes more than one unread message for the same mailbox-backed session
- **THEN** the gateway may enqueue one internal reminder prompt that summarizes the unread set observed in that cycle
- **AND THEN** the gateway does not need to enqueue one reminder per unread message

#### Scenario: Unchanged unread set does not force duplicate reminders
- **WHEN** the notifier previously delivered or enqueued a reminder for one unread set
- **AND WHEN** a later poll finds the same unread set still present and still unread
- **THEN** the gateway may treat that later poll as a duplicate and skip enqueueing a second reminder for the unchanged unread set

### Requirement: Gateway notifier records structured per-poll decision auditing for later review
When gateway-owned notifier behavior is enabled, the gateway SHALL record one structured notifier-decision audit record for each enabled poll cycle in a queryable SQLite audit table under the gateway state root.

Each record SHALL capture enough detail to explain what the notifier saw and why it enqueued or skipped work, including at minimum:

- poll time,
- unread-count observation,
- unread-set identity or equivalent deduplication summary,
- request-admission state,
- active-execution state,
- queue depth,
- the notifier decision outcome, and
- enqueue identifiers or skip detail when applicable.

The gateway MAY continue to keep `gateway.log` rate-limited and human-oriented, but that human log SHALL NOT be the only durable source of per-poll notifier decision history.

Detailed per-poll decision history SHALL remain available through that durable audit table even if `GET /v1/mail-notifier` remains a compact status snapshot without last-decision summary fields.

#### Scenario: Busy poll records an explicit skip decision
- **WHEN** a notifier poll cycle finds unread mail while gateway admission is not open, active execution is running, or queue depth is non-zero
- **THEN** the gateway records a structured audit record for that poll cycle
- **AND THEN** that record identifies the decision as a busy or ineligible skip and includes the eligibility inputs that caused the skip

#### Scenario: Enqueue poll records the created reminder request
- **WHEN** a notifier poll cycle finds unread mail and the gateway enqueues an internal reminder prompt
- **THEN** the gateway records a structured audit record for that poll cycle
- **AND THEN** that record includes the reminder decision outcome and the created internal request identifier

#### Scenario: Durable audit history remains the detailed inspection surface
- **WHEN** an operator or demo helper needs the latest detailed notifier decision data
- **THEN** it can inspect the durable SQLite notifier audit history under the gateway root
- **AND THEN** the gateway does not need to expose additional last-decision summary fields on `GET /v1/mail-notifier` in order to satisfy this requirement

### Requirement: Gateway execution adapters support REST-backed, local-headless, and server-managed targets
The gateway SHALL execute accepted terminal-mutating request kinds through an explicit execution-adapter boundary selected from durable attach metadata and manifest-backed runtime authority.

In this change, the gateway execution layer SHALL support at minimum:

- a direct REST-backed terminal adapter for the existing runtime-owned REST-backed sessions,
- a local tmux-backed adapter for runtime-owned native headless sessions and runtime-owned `local_interactive` sessions outside `houmao-server`, and
- a server-managed-agent adapter for managed-agent execution owned by `houmao-server`.

For server-managed agents, the gateway SHALL submit prompt and interrupt work through the server-owned managed-agent API rather than locally resuming the session and bypassing server-owned turn or interrupt authority.

The gateway SHALL preserve the same durable queueing, serialization, and admission semantics regardless of which execution adapter is selected.

#### Scenario: Gateway prompt for a server-managed headless agent flows through `houmao-server`
- **WHEN** a live gateway executes an accepted `submit_prompt` request for a server-managed native headless agent
- **THEN** the gateway delivers that work through the server-owned managed-agent API
- **AND THEN** the gateway does not bypass server-owned headless turn authority by privately resuming the managed session itself

#### Scenario: Gateway prompt for a runtime-owned headless session uses the local tmux-backed adapter
- **WHEN** a live gateway executes an accepted `submit_prompt` request for a runtime-owned native headless session outside `houmao-server`
- **THEN** the gateway uses the local tmux-backed execution adapter for that session
- **AND THEN** the gateway still preserves its durable request queue and single active execution slot semantics

#### Scenario: Gateway prompt for a runtime-owned local interactive session uses the local tmux-backed adapter
- **WHEN** a live gateway executes an accepted `submit_prompt` request for a runtime-owned `local_interactive` session outside `houmao-server`
- **THEN** the gateway uses the local tmux-backed execution adapter for that session
- **AND THEN** prompt delivery targets the live provider TUI through the gateway-owned queue rather than bypassing the gateway path

#### Scenario: Gateway interrupt for a runtime-owned local interactive session uses the local tmux-backed adapter
- **WHEN** a live gateway executes an accepted `interrupt` request for a runtime-owned `local_interactive` session outside `houmao-server`
- **THEN** the gateway uses the local tmux-backed execution adapter for that session
- **AND THEN** interrupt delivery targets the live provider TUI through the gateway path rather than bypassing the gateway with direct concurrent control

#### Scenario: Existing REST-backed gateway execution remains supported
- **WHEN** a live gateway executes an accepted request for an existing runtime-owned REST-backed session
- **THEN** the gateway may continue using the direct REST-backed execution adapter for that session
- **AND THEN** adding local tmux-backed or server-managed adapters does not require the REST-backed path to change its public request semantics

### Requirement: Gateway-owned TUI history exposes bounded recent tracked snapshots
For attached TUI-backed sessions whose gateway owns live tracking authority, `GET /v1/control/tui/history` SHALL return recent tracked snapshots from that gateway-owned tracking runtime rather than only coarse transition summaries.

That snapshot history SHALL be retained in memory only and SHALL be bounded to the most recent 1000 snapshots per tracked session.

The returned history SHALL be ordered from oldest retained snapshot to newest retained snapshot.

#### Scenario: Gateway TUI history returns tracked snapshots for an attached TUI session
- **WHEN** a live gateway owns TUI tracking for an attached eligible TUI-backed session
- **AND WHEN** a caller requests `GET /v1/control/tui/history`
- **THEN** the response contains recent tracked snapshots from that gateway-owned tracking runtime
- **AND THEN** the response does not collapse those snapshots to coarse transition summaries only

#### Scenario: Gateway TUI history remains bounded in memory
- **WHEN** a gateway-owned tracker for one attached TUI-backed session has recorded more than 1000 tracked snapshots
- **AND WHEN** a caller requests `GET /v1/control/tui/history`
- **THEN** the response contains at most the most recent 1000 tracked snapshots for that session
- **AND THEN** older snapshots have been evicted from in-memory history rather than persisted as durable gateway state

### Requirement: Gateway-owned TUI tracking routes support attached runtime-owned local interactive sessions
For an attached runtime-owned `local_interactive` session outside `houmao-server`, the gateway SHALL treat that session as eligible for its gateway-owned live TUI state, bounded snapshot history, and explicit prompt-note tracking surface when durable attach metadata identifies the runtime-owned session and the tmux-backed session remains available.

For this path, the gateway SHALL start one gateway-owned continuous tracking runtime for the attached session and SHALL serve `GET /v1/control/tui/state`, `GET /v1/control/tui/history`, and `POST /v1/control/tui/note-prompt` from that runtime rather than returning unsupported-backend semantics.

The gateway SHALL derive tracked-session identity from durable attach-contract fields together with optional manifest-backed enrichment and SHALL NOT require a CAO terminal id to expose this tracking surface.

For this runtime-owned local-interactive path, `GET /v1/control/tui/history` SHALL be part of the supported gateway operator workflow.

#### Scenario: Gateway-local TUI state succeeds for attached local interactive session
- **WHEN** a gateway is attached to a runtime-owned `local_interactive` session outside `houmao-server`
- **AND WHEN** the durable attach metadata identifies the runtime session id, tmux session name, and manifest path for that session
- **THEN** the gateway starts its gateway-owned tracking runtime for that session
- **AND THEN** `GET /v1/control/tui/state` succeeds using gateway-owned tracked state rather than returning an unsupported-backend response

#### Scenario: Gateway-local TUI history succeeds for attached local interactive session
- **WHEN** a gateway-owned tracking runtime is active for an attached runtime-owned `local_interactive` session
- **THEN** `GET /v1/control/tui/history` succeeds for that session
- **AND THEN** the returned history contains recent gateway-owned tracked snapshots for that same session

#### Scenario: Gateway-local prompt-note route succeeds for attached local interactive session
- **WHEN** a gateway-owned tracking runtime is active for an attached runtime-owned `local_interactive` session
- **THEN** `POST /v1/control/tui/note-prompt` succeeds for that session
- **AND THEN** the prompt note is recorded against the same gateway-owned tracked session identity used by current tracked state

### Requirement: Gateway prompt execution preserves explicit prompt-note evidence for tracked local interactive sessions
When the gateway accepts and executes `submit_prompt` for an attached runtime-owned `local_interactive` session, the gateway SHALL forward that explicit prompt-submission evidence to its gateway-owned tracking runtime for the same session.

That prompt-note behavior SHALL use the same gateway-owned tracking authority as the gateway-local TUI state and prompt-note routes for that attached session.

#### Scenario: Prompt submission updates gateway-owned tracked state for local interactive
- **WHEN** the gateway executes an accepted `submit_prompt` request for an attached runtime-owned `local_interactive` session
- **THEN** the gateway delivers the prompt through the local tmux-backed execution adapter for that session
- **AND THEN** the gateway records explicit prompt-submission evidence on the gateway-owned tracker for that same attached session
- **AND THEN** later tracked state for that session can preserve explicit-input provenance for the completed turn

### Requirement: Gateway status remains meaningful for headless sessions without TUI parsing
For headless sessions, the gateway SHALL derive execution eligibility and request-admission behavior from managed-agent execution posture rather than from parsed TUI surface classification.

The published gateway status contract SHALL remain structurally stable across transports, but headless sessions SHALL NOT require parser-owned or prompt-surface evidence in order to report whether prompt execution is currently eligible.

#### Scenario: Idle headless session reports prompt eligibility without TUI parser state
- **WHEN** a live gateway targets a managed headless session that is available and not currently running a turn
- **THEN** the gateway status reports prompt execution as eligible according to headless execution posture
- **AND THEN** the gateway does not need a parsed terminal-ready surface in order to report that eligibility

#### Scenario: Active headless turn blocks new prompt execution
- **WHEN** a live gateway targets a managed headless session that already has one active managed turn
- **THEN** the gateway status reports non-open prompt admission for that session
- **AND THEN** the gateway does not pretend that a new prompt can safely execute merely because no TUI parser is involved

### Requirement: Attached gateway becomes the authoritative per-agent control plane
When an eligible live gateway is attached to a gateway-capable managed agent session, that gateway SHALL become the authoritative per-agent control plane for live session-local control behavior for that agent.

For an attached agent, gateway-owned control behavior SHALL include at minimum:

- prompt queueing,
- readiness gating before prompt delivery,
- prompt relay to the addressed agent surface,
- interrupt sequencing,
- per-agent live execution posture, and
- per-agent lifecycle control needed to restart, stop, or kill attached work without promoting those responsibilities to the central shared server.

For attached TUI agents, this control-plane ownership SHALL apply to prompt delivery against the live TUI surface.

For attached server-managed headless agents, this control-plane ownership SHALL apply to live prompt admission and interrupt or lifecycle control for that agent even though `houmao-server` remains the durable public HTTP authority and the durable turn-inspection surface.

When no eligible live gateway is attached, this requirement does not prevent the system from using a separate direct fallback path outside the gateway capability.

#### Scenario: Attached TUI agent prompt work is admitted through the gateway
- **WHEN** a managed TUI agent has an eligible attached live gateway
- **AND WHEN** the system accepts a prompt for that agent through the public managed-agent server surface
- **THEN** live prompt queueing, readiness gating, and prompt relay for that prompt are owned by the attached gateway
- **AND THEN** the central server does not need to own a second authoritative per-agent prompt queue for that attached agent

#### Scenario: Attached server-managed headless agent uses gateway-owned live admission
- **WHEN** a server-managed headless agent has an eligible attached live gateway
- **AND WHEN** the system accepts prompt work for that agent through the public managed-agent server surface
- **THEN** live admission, queueing, and interrupt sequencing for that work are owned by the attached gateway
- **AND THEN** the central server remains the public facade and durable projection layer rather than the sole live per-agent admission owner for that attached agent

### Requirement: Gateway control roots publish read-optimized per-agent live control state
For an attached managed agent, the gateway SHALL expose read-optimized per-agent live control state through its versioned live HTTP surface so `houmao-server` and other pair-owned consumers can project current gateway-backed posture without reconstructing it from queue internals or raw tmux probing.

Those HTTP read surfaces MAY be backed by gateway control-root storage, but `houmao-server` SHALL consume attached-agent live control state through the gateway API rather than treating files under the session root as the authoritative live-state source.

For attached TUI agents, that published live control state SHALL include:

- the current tracked-state snapshot for that agent, and
- bounded recent tracked-state history for that agent.

For attached headless agents, that published live control state SHALL include:

- current execution or admission posture for that agent, and
- current queue-backed request posture for that agent.

Those read-optimized gateway-backed state artifacts or equivalent gateway-owned read surfaces SHALL remain distinct from:

- the durable request queue itself,
- raw runtime session artifacts,
- and shared-registry publication.

#### Scenario: Attached TUI gateway publishes tracked-state snapshot and history
- **WHEN** an eligible live gateway is attached to a managed TUI agent
- **THEN** the gateway control root publishes a read-optimized current tracked-state snapshot and bounded recent tracked-state history for that agent
- **AND THEN** pair-owned consumers do not need to reconstruct authoritative tracked state for that attached agent by replaying raw queue or event internals

#### Scenario: Server projects gateway-backed state without duplicating authority
- **WHEN** `houmao-server` serves managed-agent or terminal-facing state for an attached agent
- **THEN** it may consume the gateway-owned read-optimized live control state for that agent
- **AND THEN** it does not need to create a second conflicting per-agent live-state authority for the same attached agent inside the central server

#### Scenario: Server reads attached-agent live posture through gateway HTTP endpoints
- **WHEN** `houmao-server` needs current gateway-backed live state for one attached managed agent
- **THEN** it reads that state through the live gateway HTTP surface for that agent
- **AND THEN** it does not treat gateway-private session-root files as the authoritative live-state transport

### Requirement: Gateway exposes semantic prompt submission separately from raw send-keys control

For gateway-managed tmux-backed sessions, the gateway SHALL keep semantic prompt submission separate from raw key/control-input delivery.

The gateway SHALL expose two semantic prompt surfaces:

- `POST /v1/requests` as the queued gateway request surface for `submit_prompt` and `interrupt`
- `POST /v1/control/prompt` as the immediate prompt-control surface for "send now or refuse now" prompt dispatch

The gateway SHALL additionally expose a dedicated raw control-input endpoint for send-keys style delivery. That endpoint SHALL accept exact `<[key-name]>` control-input sequences using the same contract as the runtime tmux-control-input capability, including optional full-string literal escaping.

Both semantic gateway prompt surfaces SHALL treat the provided prompt body as literal text, SHALL NOT interpret `<[key-name]>` substrings as special keys, and SHALL automatically submit once at the end.

The dedicated raw control-input endpoint SHALL NOT enqueue a durable `submit_prompt` request, SHALL NOT claim that a managed prompt turn was submitted, and SHALL NOT trigger gateway prompt-submission tracking hooks by itself.

#### Scenario: Gateway direct prompt control returns immediate dispatch semantics

- **WHEN** a caller submits managed prompt work through `POST /v1/control/prompt`
- **THEN** the gateway returns success only after that prompt has been admitted for immediate live dispatch on the current target
- **AND THEN** the response does not pretend that the prompt was merely queued for later execution

#### Scenario: Gateway queued prompt submission remains on the request surface

- **WHEN** a caller submits queued gateway work through `POST /v1/requests` with kind `submit_prompt`
- **THEN** the gateway treats that work as queued semantic prompt submission rather than generic key injection
- **AND THEN** the route remains distinct from `POST /v1/control/prompt`

#### Scenario: Gateway raw send-keys uses a separate control endpoint

- **WHEN** a caller needs to inject the raw control-input sequence `"/model<[Enter]><[Down]>"` into a live gateway-managed TUI
- **THEN** the caller uses the dedicated gateway raw control-input endpoint rather than `POST /v1/requests` or `POST /v1/control/prompt`
- **AND THEN** the gateway applies the exact `<[key-name]>` parsing rules without claiming that a semantic prompt turn was submitted

#### Scenario: Gateway send-prompt keeps special-key-looking text literal

- **WHEN** a caller submits gateway prompt text `type <[Enter]> literally`
- **THEN** the gateway semantic prompt path treats `<[Enter]>` as literal text
- **AND THEN** the gateway performs one automatic final submit instead of interpreting that substring as a raw keypress

### Requirement: Gateway direct prompt control only dispatches when the addressed agent is prompt-ready unless forced

For gateway-managed prompt control through `POST /v1/control/prompt`, the gateway SHALL reject prompt dispatch by default unless the addressed target is ready to accept a new prompt immediately.

For TUI-backed sessions, the direct prompt-control path SHALL evaluate prompt readiness from the gateway-owned TUI state and SHALL require at minimum:

- `turn.phase = "ready"`
- `surface.accepting_input = "yes"`
- `surface.editing_input = "no"`
- `surface.ready_posture = "yes"`
- `stability.stable = true`

When a parsed surface is available for that TUI state, the gateway SHALL additionally require `parsed_surface.business_state = "idle"` and `parsed_surface.input_mode = "freeform"` before treating the target as prompt-ready.

For native headless sessions, the direct prompt-control path SHALL require that authoritative runtime control is operable and that no active execution or active turn is already running for that managed session.

When the request sets `force = true`, the gateway MAY bypass those prompt-readiness checks, but it SHALL still reject unavailable, reconciliation-blocked, invalid, or unsupported-target requests explicitly.

#### Scenario: Prompt-ready TUI accepts immediate prompt control

- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target
- **AND WHEN** the gateway-owned TUI state reports a stable ready posture with no active editing state
- **THEN** the gateway dispatches the prompt immediately
- **AND THEN** the success response states that the prompt was sent

#### Scenario: Busy TUI refuses direct prompt control by default

- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target
- **AND WHEN** the gateway-owned TUI state does not satisfy the prompt-ready contract
- **AND WHEN** the request does not set `force = true`
- **THEN** the gateway rejects that prompt explicitly
- **AND THEN** it does not return a success payload claiming the prompt was sent

#### Scenario: Force bypasses prompt-readiness refusal but not gateway availability failures

- **WHEN** a caller submits `POST /v1/control/prompt` with `force = true`
- **AND WHEN** the addressed target is connected but not currently prompt-ready
- **THEN** the gateway may dispatch the prompt anyway
- **AND THEN** the same route still rejects unavailable or reconciliation-blocked gateway state explicitly

#### Scenario: Headless prompt control rejects overlapping work

- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target
- **AND WHEN** that target already has active execution in flight
- **THEN** the gateway rejects that prompt explicitly
- **AND THEN** it does not start overlapping headless prompt work

#### Scenario: Unsupported backend rejects direct prompt control explicitly

- **WHEN** a caller submits `POST /v1/control/prompt` for backend `codex_app_server`
- **THEN** the gateway rejects that request as not implemented
- **AND THEN** it does not pretend that prompt readiness was evaluated successfully

### Requirement: Gateway raw send-keys bypasses prompt-readiness and busy gating

For gateway-managed raw control input through `POST /v1/control/send-keys`, the gateway SHALL forward the exact control-input request without first requiring that the addressed agent is idle, stable, or prompt-ready.

The route MAY still reject the request for ordinary gateway availability failures such as detached gateway state, reconciliation blocking, or invalid control-input payloads.

#### Scenario: Raw send-keys still forwards while the TUI is busy

- **WHEN** a caller submits `POST /v1/control/send-keys` while the gateway-owned TUI state reports active work
- **THEN** the gateway forwards that raw control-input request immediately
- **AND THEN** it does not reject the request only because the agent is not prompt-ready

### Requirement: Gateway semantic prompt submission for local interactive sessions uses the runtime semantic prompt path

When the gateway executes semantic prompt submission for an attached runtime-owned `local_interactive` session, it SHALL call the runtime semantic prompt-submission operation rather than routing prompt text through the raw send-keys control path.

For this local-interactive semantic prompt path, the gateway SHALL preserve the distinction between prompt submission and raw send-keys internally as well as on the HTTP surface.

The gateway SHALL only record gateway-owned prompt-submission tracking evidence after the semantic prompt-submission path succeeds.

#### Scenario: Gateway prompt for local interactive session uses semantic submit

- **WHEN** the gateway executes an accepted `submit_prompt` request for an attached runtime-owned `local_interactive` session
- **THEN** it calls the runtime semantic prompt-submission operation for that session
- **AND THEN** it does not implement that gateway prompt by sending raw prompt text plus Enter through the generic send-keys path

#### Scenario: Gateway raw send-keys does not create prompt-tracking evidence

- **WHEN** a caller uses the dedicated gateway raw control-input endpoint to send literal text or exact special-key tokens to an attached runtime-owned `local_interactive` session
- **THEN** the gateway does not invoke the semantic prompt-submission operation for that request
- **AND THEN** gateway-owned TUI prompt-tracking hooks do not record that raw control action as a submitted prompt turn

#### Scenario: Gateway raw send-keys does not auto-submit without explicit Enter

- **WHEN** a caller uses the dedicated gateway raw control-input endpoint to send the sequence `"hello world"` to an attached runtime-owned `local_interactive` session
- **THEN** the gateway inserts the literal text `hello world`
- **AND THEN** it does not auto-submit because the caller did not include an explicit `<[Enter]>`

### Requirement: Runtime-owned foreground gateway companions may run in an auxiliary tmux window without redefining the agent surface
For runtime-owned tmux-backed managed sessions launched through `houmao-mgr`, the system SHALL allow the gateway companion to run in a separate auxiliary tmux window in the same tmux session when foreground mode is explicitly requested.

When that foreground mode is active, the system SHALL keep tmux window `0` reserved for the managed agent surface and SHALL keep gateway output off that primary agent window.

When that foreground mode is active, the runtime SHALL treat the gateway auxiliary tmux window and pane as the authoritative local execution surface for gateway lifecycle management. It SHALL use tmux-owned pane state for local liveness, SHALL use gateway health responses for readiness, and SHALL target that auxiliary tmux surface for shutdown rather than relying on a detached subprocess handle.

The gateway companion SHALL continue writing its own durable logs to gateway-owned storage even when its console output is visible in an auxiliary tmux window.

#### Scenario: Runtime-owned foreground attach adds an auxiliary window without redefining the agent surface
- **WHEN** a gateway companion attaches later to an already-running runtime-owned tmux-backed session with explicit foreground mode enabled
- **THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion
- **AND THEN** tmux window `0` remains the canonical managed agent surface for that session
- **AND THEN** the gateway auxiliary window uses a tmux window index `>=1`

#### Scenario: Runtime-owned foreground gateway logging stays off the primary agent surface
- **WHEN** the gateway companion emits logs or diagnostics while running in an auxiliary tmux window for a runtime-owned session
- **THEN** the gateway output appears only in the auxiliary gateway window and gateway-owned durable log storage
- **AND THEN** normal gateway activity does not inject its own text into the operator-facing agent window `0`

#### Scenario: Runtime-owned foreground gateway lifecycle uses the auxiliary tmux surface
- **WHEN** the gateway companion runs in an auxiliary tmux window for a runtime-owned tmux-backed session
- **THEN** the runtime determines local gateway liveness from the auxiliary tmux pane state for that window
- **AND THEN** the runtime waits for successful gateway health responses before treating the gateway as ready
- **AND THEN** shutdown and crash cleanup target the auxiliary tmux gateway surface rather than a detached subprocess handle

