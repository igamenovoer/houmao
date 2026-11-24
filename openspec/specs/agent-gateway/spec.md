# agent-gateway Specification

## Purpose
Define the durable per-agent gateway companion, including its storage layout, HTTP surface, execution policy, and recovery behavior.
## Requirements

### Requirement: Gateway supports opt-in rotating diagnostic logs
The gateway SHALL support an opt-in diagnostic logging mode that writes bounded rotating diagnostic log files under the gateway-owned log directory.

Diagnostic logging SHALL be disabled by default when no explicit gateway diagnostic logging configuration is present.

When diagnostic logging is enabled, the gateway SHALL write line-oriented structured diagnostic entries to a dedicated diagnostic log path separate from the human-oriented `gateway.log`.

The diagnostic log configuration SHALL provide bounded retention through at least a maximum active-file size and a maximum backup-file count.

The existing `gateway.log` SHALL remain the stable human-oriented running log and SHALL NOT become the only diagnostic evidence surface for this feature.

#### Scenario: Gateway starts without diagnostic logging by default
- **WHEN** a gateway starts for a session whose gateway configuration does not enable diagnostic logging
- **THEN** the gateway keeps normal operation available
- **AND THEN** it does not create or append gateway diagnostic log entries merely because ordinary HTTP routes are called

#### Scenario: Enabled gateway writes bounded diagnostic files
- **WHEN** a gateway starts with diagnostic logging enabled and bounded rotation settings
- **THEN** the gateway writes diagnostic entries under the gateway-owned log directory
- **AND THEN** diagnostic log files rotate according to the configured maximum active-file size and backup-file count

### Requirement: Gateway diagnostic logs capture HTTP and mailbox failure evidence without raw sensitive content
When gateway diagnostic logging is enabled, the gateway SHALL record compact diagnostic entries for gateway HTTP requests and outcomes, including validation failures that occur before an endpoint handler is invoked.

Diagnostic entries for HTTP requests SHALL include at minimum method, path, status code, duration, request identifier, and diagnostic event code when those values are available.

Diagnostic entries for gateway mailbox facade operations SHALL include safe operational metadata such as operation name, transport, sender address, recipient addresses, generated message identifier when available, recipient count when available, result status, and repair guidance when applicable.

Diagnostic entries SHALL NOT include mailbox message body content, raw prompt text, attachment contents, authorization headers, cookie headers, bearer tokens, credential material, or environment secrets by default.

#### Scenario: Malformed mailbox send request is captured
- **WHEN** diagnostic logging is enabled
- **AND WHEN** a caller submits a malformed `POST /v1/mail/offline/send` request that fails request-body validation before route handling
- **THEN** the gateway records a diagnostic entry for the failed HTTP request
- **AND THEN** the entry includes the route, status code, and normalized validation error locations
- **AND THEN** the entry does not include a mailbox body or raw request body dump

#### Scenario: Mailbox delivery failure records repair context safely
- **WHEN** diagnostic logging is enabled
- **AND WHEN** a gateway mailbox send reaches mailbox delivery but fails because mailbox-local state is unreadable or missing
- **THEN** the gateway records a diagnostic entry for the mailbox failure
- **AND THEN** the entry includes the operation, transport, safe participant metadata, error category, and repair hint when available
- **AND THEN** the entry does not include the message body or attachment contents

### Requirement: Gateway diagnostic logging deduplicates consecutive warning and error entries
When gateway diagnostic logging is enabled, the gateway SHALL deduplicate consecutive warning or error diagnostic entries that share the same semantic deduplication key.

The deduplication key SHALL ignore volatile values such as timestamp, duration, request identifier, and generated message identifier while preserving event code, route, HTTP status, error category, and normalized validation field paths.

The gateway SHALL write the first warning or error entry in a consecutive duplicate run normally, suppress later consecutive duplicates with the same key, and emit a summary entry with the suppressed count when the run ends or when diagnostic logging is flushed.

Diagnostic logging SHALL NOT deduplicate ordinary informational entries unless they are explicitly modeled as warning or error summaries.

#### Scenario: Consecutive equivalent validation errors are summarized
- **WHEN** diagnostic logging is enabled
- **AND WHEN** several consecutive requests fail with the same validation error shape on the same route
- **THEN** the gateway writes the first warning or error diagnostic entry
- **AND THEN** it suppresses later consecutive duplicates with the same semantic key
- **AND THEN** it emits a summary entry reporting how many duplicate diagnostics were suppressed

#### Scenario: Different error breaks a deduplication run
- **WHEN** diagnostic logging is enabled
- **AND WHEN** a warning or error diagnostic entry differs by route, status, event code, error category, or normalized validation field paths from the previous suppressed run
- **THEN** the gateway flushes the previous suppressed-count summary before recording the different diagnostic entry

### Requirement: Per-agent gateway companion defaults tmux-backed managed sessions to same-session foreground execution and may attach after session start
The system SHALL support a per-agent gateway companion for gateway-capable tmux-backed sessions.

For tmux-backed managed sessions, managed attach and launch-time auto-attach SHALL default the effective gateway execution mode to same-session foreground auxiliary-window execution unless the operator explicitly requests background mode.

When explicit background mode is requested for a tmux-backed managed session, the gateway companion SHALL use detached execution and SHALL NOT require or create a visible tmux window or pane for normal operation.

When foreground same-session mode is active, the gateway companion MAY run in an auxiliary tmux window in the same tmux session so long as that auxiliary window does not redefine the contractual managed-agent surface.

The gateway companion MAY be started immediately after a managed session starts or later by attaching to an already-running tmux-backed session.

The gateway companion SHALL direct its own logs away from the contractual operator-facing agent surface. When foreground mode is active, gateway console output SHALL appear only in the auxiliary gateway window and gateway-owned durable log storage, not on the agent surface in tmux window `0`.

#### Scenario: Default attach-later uses same-session foreground execution
- **WHEN** a gateway companion attaches to an already-running tmux-backed managed session without an explicit background override
- **THEN** the effective execution mode is same-session foreground auxiliary-window execution
- **AND THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion

#### Scenario: Default launch-time auto-attach uses same-session foreground execution
- **WHEN** a tmux-backed managed session starts with launch-time gateway auto-attach enabled
- **AND WHEN** no explicit background override is requested for that launch
- **THEN** the effective gateway execution mode is same-session foreground auxiliary-window execution
- **AND THEN** the live gateway does not reuse tmux window `0`

#### Scenario: Explicit background mode avoids a visible gateway window
- **WHEN** a gateway companion attaches to a tmux-backed managed session with explicit background mode enabled
- **THEN** the effective execution mode is detached background execution
- **AND THEN** the attach flow does not require creating a visible tmux pane or window for the gateway

#### Scenario: Pair-managed same-session gateway does not redefine the contractual agent surface
- **WHEN** a managed gateway companion runs in an auxiliary tmux window in the same tmux session
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
For pair-managed tmux-backed `houmao_server_rest` sessions, the system SHALL default the gateway companion to same-session auxiliary-window execution for normal operation unless explicit background mode is requested.

When explicit background mode is requested for a pair-managed `houmao_server_rest` session, the system SHALL attach or reuse the gateway in detached execution instead of creating or reusing the same-session auxiliary tmux window for that attach.

When the gateway companion runs in the same tmux session, the system SHALL keep tmux window `0` reserved for the managed agent surface and SHALL keep gateway output off that primary agent window.

When the gateway companion runs in the same tmux session, the runtime SHALL treat the gateway auxiliary tmux window and pane as the authoritative local execution surface for gateway lifecycle management. It SHALL use tmux-owned pane state for local liveness, SHALL use gateway health responses for readiness, and SHALL target that auxiliary tmux surface for shutdown rather than relying on a detached subprocess handle.

The gateway companion SHALL continue writing its own durable logs to gateway-owned storage even when its console output is visible in an auxiliary tmux window.

The `houmao-server` process and its internal compatibility support state SHALL remain outside the agent's tmux session even when the gateway companion runs in the same managed session as the agent.

#### Scenario: Default pair-managed attach adds an auxiliary window without redefining the agent surface
- **WHEN** a gateway companion attaches later to an already-running pair-managed `houmao_server_rest` session without an explicit background override
- **THEN** the attach flow creates or reuses an auxiliary tmux window for the gateway companion
- **AND THEN** tmux window `0` remains the canonical managed agent surface for that session

#### Scenario: Pair-managed explicit background attach skips the auxiliary window
- **WHEN** a gateway companion attaches to a pair-managed `houmao_server_rest` session with explicit background mode enabled
- **THEN** the attach flow uses detached background execution for that attach
- **AND THEN** it does not create or reuse a same-session auxiliary tmux window for the gateway

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
For runtime-owned tmux-backed managed sessions launched through `houmao-mgr`, the system SHALL allow the gateway companion to run in a separate auxiliary tmux window in the same tmux session whenever foreground mode is the effective execution mode, whether selected by default or by an explicit override.

When that foreground mode is active, the system SHALL keep tmux window `0` reserved for the managed agent surface and SHALL keep gateway output off that primary agent window.

When that foreground mode is active, the runtime SHALL treat the gateway auxiliary tmux window and pane as the authoritative local execution surface for gateway lifecycle management. It SHALL use tmux-owned pane state for local liveness, SHALL use gateway health responses for readiness, and SHALL target that auxiliary tmux surface for shutdown rather than relying on a detached subprocess handle.

The gateway companion SHALL continue writing its own durable logs to gateway-owned storage even when its console output is visible in an auxiliary tmux window.

#### Scenario: Runtime-owned default foreground attach adds an auxiliary window without redefining the agent surface
- **WHEN** a gateway companion attaches later to an already-running runtime-owned tmux-backed session without an explicit background override
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

### Requirement: Gateway attach supports explicit tmux-session targeting outside the owning session
`houmao-mgr agents single --target-tmux-session <session> gateway attach` SHALL select a unique fresh local registry record. Attach SHALL verify that the manifest matches the selected agent, generation, and owning tmux binding.

#### Scenario: Acceptance criteria

- **WHEN** an operator attaches a gateway with a tmux session alias
- **THEN** the runtime uses the current selected owner's authority

#### Scenario: Outside-tmux attach resolves authority from the addressed tmux session manifest

- **WHEN** a caller selects a fresh registry alias for a peer on another socket
- **THEN** the manager uses the peer's verified manifest and owner socket to attach the gateway
- **AND THEN** the caller's enclosing tmux session is unaffected

#### Scenario: Outside-tmux attach falls back to shared-registry tmux alias recovery

- **WHEN** one fresh registry alias identifies the intended local agent
- **AND WHEN** the caller cannot read the enclosing tmux environment
- **THEN** the manager resolves the owner manifest directly from the registry

#### Scenario: Pair-managed attach uses manifest-derived pair authority after tmux-session resolution

- **WHEN** a local registry alias refers to a retired pair-managed backend
- **THEN** the manager reports that the backend is retired
- **AND THEN** pair selection uses an explicit agent ID or name

#### Scenario: Conflicting registry alias fails closed

- **WHEN** multiple fresh records claim the same tmux alias
- **THEN** the manager reports the candidate agent IDs and requests an explicit selector

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

Allowed listener hosts in this change are exactly `127.0.0.1` and `0.0.0.0`. Binding to `0.0.0.0` SHALL require valid explicit access settings and initialized owner access state before live publication or plugin activation. Both listeners SHALL apply the same route access rules, including the admin list's empty state.

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
- **WHEN** the system starts a gateway companion with resolved gateway host `0.0.0.0`, port `43123`, and valid explicit access settings and owner state
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

#### Scenario: Broader binding requires explicit access policy

- **WHEN** an operator selects `0.0.0.0` without valid explicit access settings or initialized owner state
- **THEN** startup fails before live publication or plugin activation
- **AND** there is no live gateway publication from that attempt

### Requirement: The gateway exposes a structured HTTP API on the resolved listener address
The gateway SHALL expose an HTTP API for health, endpoint discovery, enabled public input, status, gateway-managed request submission, reminders, notifier control, and shared mailbox operations on the resolved listener address. Route admission SHALL enforce the selected target's public, private, and admin access classes.

The base API SHALL include public `GET /health` and `GET /v1/endpoint`, private `GET /v1/status`, and admin `POST /v1/requests`. The public input setting SHALL enable `POST /v1/messages` and `POST /v1/public/prompt`. Those two routes SHALL use the public handoff contract.

The gateway SHALL expose public `POST /v1/auth/challenge` for self, admin, and first-key registration proof. Admin `POST /v1/admin/keys` and `DELETE /v1/admin/keys/{key_id}` SHALL apply the live membership contract, including first registration on a running gateway with a valid empty list.

The reminder HTTP API SHALL additionally expose `POST /v1/reminders`, `GET /v1/reminders`, `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, and `DELETE /v1/reminders/{reminder_id}`.

The HTTP API SHALL expose the private dual-binding summary `GET /v1/mail/status` and channel-selected lifecycle routes `POST /v1/mail/{channel}/{operation}` for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`. Routine lifecycle operations SHALL be private and operator-origin `post` SHALL be admin. The channel SHALL be explicitly `offline` or `online`, and lifecycle requests SHALL identify the expected binding ID.

When the gateway mail notifier capability is implemented, that HTTP API SHALL additionally expose `PUT /v1/mail-notifier/{channel}`, `GET /v1/mail-notifier/{channel}`, and `DELETE /v1/mail-notifier/{channel}`.

Public `GET /health` SHALL return only process health and gateway protocol-version information in a structured response suitable for runtime launch-readiness checks.

`GET /health` SHALL reflect gateway-local process and control-plane health, and SHALL NOT fail solely because the managed agent is unavailable, recovering, or awaiting rebind.

Private `GET /v1/status` SHALL return the same versioned status model that the gateway persists to `state.json`.

`POST /v1/requests` SHALL accept typed request-creation payloads and SHALL return the accepted queued request record.

The reminder routes SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to mutate gateway memory or private runtime objects directly.

The reminder request models SHALL support either semantic `prompt` delivery or raw `send_keys` delivery, but SHALL require exactly one of those delivery forms for each reminder definition.

Reminder-route validation failures SHALL return HTTP `422`. Unknown reminder identifiers on `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, or `DELETE /v1/reminders/{reminder_id}` SHALL return HTTP `404`.

The notifier control endpoints SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write gateway SQLite state directly.

The shared mailbox routes SHALL be limited to mailbox status, listing, peeking, reading, ordinary `send`, operator-origin `post`, `reply`, explicit marking, moving, and archive behavior.

Ordinary `send`, `reply`, read, mark, move, and archive behavior SHALL continue using the shared mailbox abstraction across both the filesystem and `stalwart` transports. Operator-origin `post` SHALL support only filesystem mailbox bindings in v1 and SHALL fail explicitly for other transports.

Those shared mailbox routes SHALL use structured request and response payloads and SHALL NOT require callers to read or write transport-local SQLite state, filesystem `rules/`, or Stalwart-native objects directly.

That HTTP API SHALL be served by the gateway sidecar itself and SHALL use structured request and response payloads rather than requiring callers to read or write SQLite state directly.

Missing or invalid required proof SHALL return HTTP `401` with applicable challenge information before request processing. Request-validation failures on admitted `POST /v1/requests` SHALL return HTTP `422`. Insufficient authority SHALL return HTTP `403`. Request-state conflicts such as reconciliation-required admission blocking SHALL return HTTP `409`. Managed-agent unavailable or recovery-blocked admission failures SHALL return HTTP `503`.

Notifier validation failures SHALL return HTTP `422`. Attempts to enable notifier behavior for sessions that cannot support it SHALL fail explicitly rather than pretending that notifier polling is active.

Shared mailbox route validation failures SHALL return HTTP `422`. Summary status SHALL remain a normal empty-binding response when neither slot is configured. Lifecycle calls selecting an absent binding SHALL fail explicitly. Unqualified lifecycle routes SHALL NOT infer a channel. Protected mailbox routes SHALL apply caller authority and binding checks on loopback and broader listeners.

Read-oriented HTTP endpoints and mailbox read routes SHALL NOT consume the terminal-mutation slot solely to report current gateway health, core status, reminder state, notifier status, or shared mailbox state.

#### Scenario: Reminder registration uses the live gateway HTTP surface
- **WHEN** a caller needs to register, inspect, update, or cancel live reminders for an attached gateway-managed session
- **THEN** the caller uses the dedicated `/v1/reminders` route family on that live gateway listener
- **AND THEN** the caller does not need to mutate private runtime state or transport queue artifacts directly

#### Scenario: Send-keys reminder request is validated through the reminder route family
- **WHEN** a caller submits a reminder definition with `send_keys` through `/v1/reminders`
- **THEN** the reminder request is validated on that reminder route family
- **AND THEN** the caller does not need to use a separate reminder-specific control-input route

#### Scenario: Unknown reminder identifier fails explicitly
- **WHEN** a caller requests `GET /v1/reminders/{reminder_id}`, `PUT /v1/reminders/{reminder_id}`, or `DELETE /v1/reminders/{reminder_id}` for a non-existent reminder
- **THEN** the gateway rejects that call explicitly
- **AND THEN** it does not pretend that the requested reminder still exists

### Requirement: Gateway status separates gateway health, upstream-agent state, recovery, admission, surface eligibility, and execution state
The gateway SHALL publish a structured status model that separates gateway health from managed-agent connectivity, recovery state, request-admission state, and native-surface readiness.

That published status model SHALL be protocol-versioned and SHALL be shared by both `state.json` and `GET /v1/status`.

At minimum, the published gateway status SHALL distinguish:

- protocol version
- stable session identity
- current managed-agent instance epoch
- gateway health state
- managed-agent connectivity state
- managed-agent recovery state
- request-admission state
- native-surface kind and eligibility state
- active execution state
- gateway execution mode
- gateway host
- gateway port
- queue depth

When the gateway is running in `tmux_auxiliary_window` mode, the published gateway status SHALL additionally expose the authoritative tmux execution handle for that live gateway surface, including the tmux window index and tmux window identifier. It MAY also expose the tmux pane identifier.

When the gateway cannot safely classify the managed native surface, it SHALL publish an explicit unknown-like state rather than inferring readiness.

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
- **THEN** the gateway updates the published native-surface eligibility state to reflect that non-ready surface
- **AND THEN** the gateway does not mark itself unhealthy solely because the operator changed the TUI surface

#### Scenario: Foreground gateway status exposes the tmux execution handle
- **WHEN** the gateway companion runs in `tmux_auxiliary_window` mode
- **THEN** the published status includes `execution_mode=tmux_auxiliary_window`
- **AND THEN** the published status exposes the authoritative tmux window index and tmux window identifier for that live gateway surface

#### Scenario: Uncertain surface classification stays explicit
- **WHEN** the gateway cannot safely determine whether the managed native surface is ready for injection
- **THEN** the gateway publishes an explicit non-ready or unknown-like surface state
- **AND THEN** it does not silently treat the surface as submit-ready

#### Scenario: Web Readiness Does Not Depend on a Terminal Parser
- **WHEN** the attached agent's native surface is Web
- **THEN** status exposes its Web identity, native readiness, pending-input, and execution facts
- **AND THEN** a healthy supervisory tmux pane cannot substitute for native Web readiness

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

### Requirement: Gateway coalesces adjacent queued control intents
The gateway SHALL coalesce adjacent accepted queued control-intent records before those records execute against the managed agent.

Control-intent records SHALL be limited to queued `interrupt` requests and queued `submit_prompt` requests whose entire trimmed prompt exactly matches a recognized context-control command. The initial recognized context-control commands SHALL include `/compact`, `/clear`, and `/new`.

The gateway SHALL treat ordinary prompts, internal `mail_notifier_prompt` records, unsupported stored request kinds, and different managed-agent instance epochs as coalescing boundaries. The gateway SHALL NOT coalesce `running`, `completed`, `failed`, or already `coalesced` records.

The gateway SHALL preserve ordinary prompt order and content exactly.

#### Scenario: Duplicate interrupts collapse to one interrupt
- **WHEN** the accepted queue contains an adjacent run of multiple `interrupt` requests for the same managed-agent instance epoch
- **THEN** the gateway executes at most one interrupt for that run
- **AND THEN** the redundant interrupt records are marked as coalesced instead of running independently

#### Scenario: Duplicate context command prompts collapse to one prompt
- **WHEN** the accepted queue contains adjacent `submit_prompt` records whose trimmed prompts are all `/compact`
- **THEN** the gateway executes at most one `/compact` prompt for that run
- **AND THEN** the redundant `/compact` records are marked as coalesced instead of running independently

#### Scenario: Later context commands supersede earlier pending context commands
- **WHEN** the accepted queue contains an adjacent run of context-control prompts `/compact`, `/clear`, and `/new` for the same managed-agent instance epoch
- **THEN** the gateway executes only the strongest final effective context action for that run
- **AND THEN** `/new` supersedes pending `/clear` and `/compact`, and `/clear` supersedes pending `/compact`

#### Scenario: Mixed interrupt and context commands preserve one interrupt intent
- **WHEN** the accepted queue contains an adjacent run with one or more `interrupt` records and one or more recognized context-control prompt records for the same managed-agent instance epoch
- **THEN** the gateway preserves one effective interrupt intent and one final effective context-control prompt
- **AND THEN** the effective interrupt executes before the effective context-control prompt

#### Scenario: Ordinary prompts break coalescing runs
- **WHEN** an ordinary `submit_prompt` record appears between two control-intent records in the accepted queue
- **THEN** the gateway treats the ordinary prompt as a hard coalescing boundary
- **AND THEN** the gateway preserves the ordinary prompt order and does not merge control intents across it

#### Scenario: Internal notifier prompts are not coalesced
- **WHEN** an accepted internal `mail_notifier_prompt` record appears in the queue
- **THEN** the gateway does not classify that record as a coalescible control intent
- **AND THEN** the gateway does not merge ordinary or control work across that notifier record

#### Scenario: Epoch boundaries prevent coalescing
- **WHEN** adjacent accepted control-intent records have different `managed_agent_instance_epoch` values
- **THEN** the gateway does not coalesce those records together
- **AND THEN** existing replay and reconciliation safeguards remain authoritative for old-epoch work

#### Scenario: Coalescing leaves durable audit evidence
- **WHEN** the gateway removes an accepted request from execution by coalescing it into effective control work
- **THEN** the gateway marks that request with terminal state `coalesced`
- **AND THEN** the gateway records enough result metadata and gateway event data to identify the effective request or action that superseded it

#### Scenario: Coalesced records do not count as active queue depth
- **WHEN** a request has terminal state `coalesced`
- **THEN** gateway queue-depth reporting excludes that request
- **AND THEN** only accepted and running work contributes to active queue depth

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
When gateway-owned notifier behavior is enabled for a mailbox-backed session, the gateway SHALL treat notification eligibility as a function of whether unread mail exists for that session and whether the session is currently eligible to receive a reminder prompt.

If a poll cycle finds multiple unread messages, the gateway SHALL support satisfying notifier behavior with a single internal reminder prompt that summarizes the unread set for that cycle, including message metadata such as titles or identifiers.

The gateway SHALL NOT require one internal reminder prompt per unread message in order to satisfy notifier behavior.

If the unread set remains unchanged after an earlier reminder was delivered or enqueued, and a later poll finds the session eligible to accept a new prompt again, the gateway SHALL continue treating that unchanged unread set as eligible for another reminder.

The gateway SHALL NOT suppress a later reminder solely because a prior reminder targeted the same unread snapshot.

#### Scenario: Multiple unread messages can be summarized in one reminder prompt
- **WHEN** one notifier poll cycle observes more than one unread message for the same mailbox-backed session
- **THEN** the gateway may enqueue one internal reminder prompt that summarizes the unread set observed in that cycle
- **AND THEN** the gateway does not need to enqueue one reminder per unread message

#### Scenario: Unchanged unread set remains eligible after the session becomes ready again
- **WHEN** the notifier previously delivered or enqueued a reminder for one unread set
- **AND WHEN** a later poll finds the same unread set still present and still unread
- **AND WHEN** the managed session is again eligible to accept a new prompt
- **THEN** the gateway continues treating that unread set as eligible for another reminder
- **AND THEN** it does not suppress that later reminder solely because the unread snapshot is unchanged

#### Scenario: Operator activity does not retire unread reminder eligibility
- **WHEN** unread mail remains present after a prior reminder
- **AND WHEN** operator-driven commands or other unrelated session activity interrupt, replace, or sidetrack the earlier reminder flow
- **AND WHEN** a later poll finds the managed session eligible to accept a new prompt again
- **THEN** the gateway still treats the remaining unread mail as eligible for notifier reminder delivery
- **AND THEN** reminder eligibility continues to depend on unread mail plus live prompt readiness rather than on prior reminder history

### Requirement: Gateway notifier records structured per-poll decision auditing for later review
When gateway-owned notifier behavior is enabled, the gateway SHALL record one structured notifier-decision audit record for each enabled poll cycle in a queryable SQLite audit table under the gateway state root.

Each record SHALL capture enough detail to explain what the notifier saw and why it enqueued or skipped work, including at minimum:

- poll time,
- owner, selected channel, and binding identity,
- unread-count observation,
- unread-set identity or equivalent deduplication summary,
- request-admission state,
- active-execution state,
- queue depth,
- the notifier decision outcome, and
- enqueue identifiers or skip detail when applicable.

The gateway MAY continue to keep `gateway.log` rate-limited and human-oriented, but that human log SHALL NOT be the only durable source of per-poll notifier decision history.

Detailed per-poll decision history SHALL remain available through that durable audit table even if `GET /v1/mail-notifier/{channel}` remains a compact status snapshot without last-decision summary fields.

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
- **AND THEN** the gateway does not need to expose additional last-decision summary fields on `GET /v1/mail-notifier/{channel}` in order to satisfy this requirement

### Requirement: Gateway execution adapters support REST-backed, local-headless, and server-managed targets
The gateway SHALL execute accepted terminal-mutating request kinds through an explicit execution-adapter boundary selected from durable attach metadata and manifest-backed runtime authority. The gateway SHALL bind managed work to the recorded run mode, current owner generation, and supported operations before dispatch. A supervisor pane or reachable listener alone SHALL NOT authorize a fallback adapter.

In this change, the gateway execution layer SHALL support at minimum:

- a direct REST-backed terminal adapter for the existing runtime-owned REST-backed sessions,
- a local tmux-backed adapter for runtime-owned native headless and `local_interactive` sessions,
- a structured native adapter for the existing `dsh_web` owner, and
- a passive-server backing adapter for headless execution admitted by `houmao-passive-server`.

For passive-server-owned headless agents, the gateway SHALL submit prompt and interrupt work through the admitted passive backing API so both surfaces preserve a single turn authority. Retained REST-backed sessions continue to use their saved authority.

The gateway SHALL preserve the same durable queueing, serialization, and admission semantics regardless of which execution adapter is selected.

#### Scenario: Gateway prompt for a server-managed headless agent flows through `houmao-server`
- **WHEN** a live gateway executes an accepted `submit_prompt` request for a server-managed native headless agent
- **THEN** the gateway delivers that work through the admitted passive backing API
- **AND THEN** the gateway preserves the passive server's managed headless turn authority

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

#### Scenario: Detached owner refuses stale control

- **WHEN** a gateway holds an execution handle from before owner replacement
- **THEN** the gateway rejects dispatch on that handle and resolves the current owner before accepting more work

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

### Requirement: Gateway exposes explicit headless chat-session state and next-prompt override control
For native headless gateway targets, the live gateway SHALL expose dedicated headless chat-session control routes:

- `GET /v1/control/headless/state`
- `POST /v1/control/headless/next-prompt-session`

`GET /v1/control/headless/state` SHALL return the gateway's current headless control-state payload for the addressed managed session.

That payload SHALL include a `chat_session` state object with at least:

- `current`, describing the concrete provider session currently pinned by the managed agent or `null` when none is pinned
- `startup_default`, describing the managed agent's first-chat fallback policy using one of `new`, `tool_last_or_new`, or `exact`
- `next_prompt_override`, containing either `null` or a one-shot override object

When `startup_default.mode = exact`, the state payload SHALL include the exact provider session id used by that startup default.

In v1, `POST /v1/control/headless/next-prompt-session` SHALL be valid only for native headless gateway targets and SHALL accept only `mode = new`. It SHALL set `chat_session.next_prompt_override` so the next accepted prompt whose effective selector is `auto` uses a fresh provider chat.

That one-shot override SHALL:

- be gateway-local live state rather than durable persisted state,
- be lost if the gateway stops or restarts,
- be consumed only when the next accepted `auto` prompt is admitted,
- remain pending when a later prompt explicitly requests `new`, `current`, `tool_last_or_new`, or `exact`,
- not affect queued gateway requests, wakeup delivery, mail-notifier behavior, or other internal gateway-generated prompts.

`POST /v1/control/headless/next-prompt-session` SHALL return the updated headless control-state payload after storing the pending override.

For TUI-backed or otherwise non-headless targets, both routes SHALL reject the request with validation semantics rather than pretending that a headless control surface exists.

#### Scenario: Headless state reports current session, startup default, and pending override
- **WHEN** a caller requests `GET /v1/control/headless/state` for a native headless gateway target
- **THEN** the response includes `chat_session.current`, `chat_session.startup_default`, and `chat_session.next_prompt_override`
- **AND THEN** the caller can distinguish the managed agent's pinned current session from its startup policy and one-shot override posture

#### Scenario: Next-prompt override is consumed by the next accepted auto prompt
- **WHEN** a caller first submits `POST /v1/control/headless/next-prompt-session` with `mode = new`
- **AND WHEN** the next accepted public `POST /v1/control/prompt` for that same headless target omits `chat_session` or explicitly sets `chat_session.mode = auto`
- **THEN** that prompt uses a fresh provider chat
- **AND THEN** a later `GET /v1/control/headless/state` no longer reports a pending next-prompt override

#### Scenario: Explicit non-auto prompt does not consume the pending next-prompt override
- **WHEN** a caller first submits `POST /v1/control/headless/next-prompt-session` with `mode = new`
- **AND WHEN** a later accepted `POST /v1/control/prompt` for that same headless target explicitly requests `chat_session.mode = current`
- **THEN** the gateway resolves that prompt using the explicit selector
- **AND THEN** the pending next-prompt override remains visible until a later accepted auto prompt consumes it or the gateway stops

#### Scenario: Restart clears the pending next-prompt override
- **WHEN** a native headless gateway target has a pending next-prompt override
- **AND WHEN** the gateway stops or restarts before an accepted auto prompt consumes it
- **THEN** the restarted gateway no longer reports that pending override
- **AND THEN** the override is not recovered from durable gateway state

#### Scenario: TUI target rejects headless chat-session control routes
- **WHEN** a caller requests `GET /v1/control/headless/state` or `POST /v1/control/headless/next-prompt-session` for a TUI-backed gateway target
- **THEN** the gateway rejects that request with validation semantics
- **AND THEN** it does not pretend that a headless control surface exists for that target

### Requirement: Gateway exposes semantic prompt submission separately from raw send-keys control

For gateway-managed tmux-backed sessions, the gateway SHALL keep semantic prompt submission separate from raw key/control-input delivery.

The gateway SHALL expose two semantic prompt surfaces:

- `POST /v1/requests` as the queued gateway request surface for `submit_prompt` and `interrupt`
- `POST /v1/control/prompt` as the immediate prompt-control surface for "send now or refuse now" prompt dispatch

For native headless targets, `POST /v1/control/prompt` SHALL additionally accept an optional structured `chat_session` selector object.

That headless-only selector SHALL use:

- `chat_session.mode = auto | new | current | tool_last_or_new | exact`
- `chat_session.id` required only when `mode = exact`

For headless prompt control:

- omitting `chat_session` SHALL be equivalent to `chat_session.mode = auto`
- `new` SHALL mean "use a fresh provider chat for this prompt"
- `current` SHALL mean "use the managed agent's pinned current provider session"
- `tool_last_or_new` SHALL mean "ask the underlying tool to resume its latest stored chat and start fresh if none exists"
- `exact` SHALL mean "use this exact provider session identifier"

The gateway SHALL additionally expose a dedicated raw control-input endpoint for send-keys style delivery. That endpoint SHALL accept exact `<[key-name]>` control-input sequences using the same contract as the runtime tmux-control-input capability, including optional full-string literal escaping.

Both semantic gateway prompt surfaces SHALL treat the provided prompt body as literal text, SHALL NOT interpret `<[key-name]>` substrings as special keys, and SHALL automatically submit once at the end.

The dedicated raw control-input endpoint SHALL NOT enqueue a durable `submit_prompt` request, SHALL NOT claim that a managed prompt turn was submitted, and SHALL NOT trigger gateway prompt-submission tracking hooks by itself.

For TUI-backed targets, `POST /v1/control/prompt` SHALL accept `chat_session.mode = new` and SHALL reject `chat_session.mode = auto | current | tool_last_or_new | exact` with validation semantics rather than ignoring the field.

Malformed `chat_session` payloads, including missing `id` for `exact` or unexpected `id` for other modes, SHALL be rejected with validation semantics.

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

#### Scenario: Headless direct prompt control accepts explicit tool-native latest selection
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target with `chat_session.mode = tool_last_or_new`
- **THEN** the gateway resolves that request by asking the tool to resume its latest stored chat or start fresh if none exists
- **AND THEN** the gateway does not reinterpret that selector as the managed agent's current pinned session

#### Scenario: TUI direct prompt control accepts explicit new-session reset request
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target with `chat_session.mode = new`
- **THEN** the gateway accepts that request as a TUI conversation-reset workflow
- **AND THEN** it does not reinterpret that selector as headless provider-session state

#### Scenario: TUI direct prompt control rejects unsupported explicit session selector
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target with `chat_session.mode = current`
- **THEN** the gateway rejects that request with validation semantics
- **AND THEN** it does not ignore the selector and pretend that ordinary prompt control succeeded

### Requirement: Degraded chat context does not force clean-context prompt control
Gateway prompt control SHALL treat recoverable degraded chat context as compatible with ordinary current-context prompt delivery when the target otherwise satisfies the prompt-ready contract.

For native headless targets, recoverable degraded chat context SHALL NOT by itself force the effective chat-session selector to `chat_session.mode = new`.

For TUI-backed targets, recoverable degraded chat context SHALL NOT by itself trigger the reset-then-send workflow.

Explicit clean-context requests SHALL remain supported. When a caller explicitly requests `chat_session.mode = new`, the gateway SHALL preserve the existing headless fresh-chat selection and TUI reset-then-send behavior for targets that support that selector.

#### Scenario: Ordinary TUI prompt continues degraded current context
- **GIVEN** a TUI-backed gateway target whose tracked state is prompt-ready and whose chat context is recoverably degraded
- **WHEN** a caller submits direct prompt control without a `chat_session` selector
- **THEN** the gateway sends the caller's prompt through the ordinary TUI prompt path
- **AND THEN** the gateway does not first send `/new`, `/clear`, or another context-reset signal solely because degraded context is present

#### Scenario: Explicit TUI new-chat prompt still resets
- **GIVEN** a TUI-backed gateway target whose tracked state is prompt-ready
- **WHEN** a caller submits direct prompt control with `chat_session.mode = new`
- **THEN** the gateway runs the supported TUI reset-then-send workflow
- **AND THEN** the caller's actual prompt is sent only after the reset workflow reaches prompt-ready posture

#### Scenario: Ordinary headless prompt does not force new chat for degraded context
- **GIVEN** a native headless gateway target whose chat context is recoverably degraded
- **WHEN** a caller submits prompt control without an explicit clean-context selector
- **THEN** the gateway resolves the prompt's chat-session selector using the ordinary current-context rules
- **AND THEN** the dispatched request body does not include `chat_session.mode = new` solely because degraded context is present

#### Scenario: Explicit headless new-chat prompt remains supported
- **GIVEN** a native headless gateway target
- **WHEN** a caller submits prompt control with `chat_session.mode = new`
- **THEN** the gateway dispatches the prompt with a fresh provider-chat selection

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

### Requirement: Gateway supports ephemeral ranked reminder records
The live gateway SHALL expose dedicated reminder routes for direct timer-backed reminder registration without requiring mailbox participation.

That reminder surface SHALL include:

- `POST /v1/reminders`
- `GET /v1/reminders`
- `GET /v1/reminders/{reminder_id}`
- `PUT /v1/reminders/{reminder_id}`
- `DELETE /v1/reminders/{reminder_id}`

Each reminder record SHALL include:

- a non-empty `title`
- exactly one delivery form:
  - a non-empty semantic `prompt`, or
  - a `send_keys` object with a non-empty `sequence`
- a `delivery_kind` inspection value that distinguishes `prompt` from `send_keys`
- a signed `ranking` value whose ordering is ascending and is not restricted to non-negative values
- a `paused` flag
- either one-off scheduling with exactly one requested due time or repeating scheduling with an interval and next due time

The reminder `send_keys` object SHALL support:

- `sequence`
- `ensure_enter`, defaulting to `true`

The gateway SHALL keep registered reminders entirely in the live gateway process memory. Pending reminders and due-but-not-yet-executed reminder occurrences SHALL NOT survive gateway shutdown or restart.

The live gateway SHALL nominate exactly one effective reminder at a time using this deterministic order:

1. smallest `ranking`
2. earliest `created_at`
3. smallest `reminder_id` in lexical order

All non-effective reminders SHALL remain blocked behind that selected reminder even when they are already due.

Deleting a reminder SHALL remove that reminder while it remains registered. If execution of one reminder occurrence has already started, deleting the reminder SHALL NOT retroactively retract that already-started reminder execution.

Unknown `reminder_id` lookups, updates, or deletions SHALL fail explicitly rather than pretending the reminder still exists.

When a reminder uses `send_keys`, the gateway SHALL validate support for raw control input against the current attached gateway target during create and update. If the attached target cannot preserve exact raw control-input semantics, the gateway SHALL reject that reminder definition explicitly instead of accepting it for later failure.

#### Scenario: Caller registers a prompt reminder
- **WHEN** a caller submits `POST /v1/reminders` with a reminder definition containing a non-empty `prompt` and no `send_keys`
- **THEN** the live gateway creates that reminder successfully
- **AND THEN** the created reminder reports `delivery_kind = "prompt"`

#### Scenario: Caller registers a send-keys reminder
- **WHEN** a caller submits `POST /v1/reminders` with a reminder definition containing `send_keys.sequence`
- **THEN** the live gateway creates that reminder successfully when the attached target supports raw control input
- **AND THEN** the created reminder reports `delivery_kind = "send_keys"`

#### Scenario: Smallest ranking becomes the effective reminder
- **WHEN** the live gateway holds reminder records with different ranking values
- **THEN** the reminder with the smallest ranking value is the effective reminder
- **AND THEN** all higher-ranking reminders remain blocked until the effective reminder is updated or removed

#### Scenario: Reminder definition with both delivery forms is rejected
- **WHEN** a caller submits a reminder definition that includes both `prompt` and `send_keys`
- **THEN** the gateway rejects that reminder definition explicitly
- **AND THEN** it does not accept an ambiguous delivery mode

#### Scenario: Unsupported backend rejects a send-keys reminder
- **WHEN** a caller submits or updates a reminder definition with `send_keys`
- **AND WHEN** the current attached gateway target cannot preserve raw control-input semantics
- **THEN** the gateway rejects that reminder definition explicitly
- **AND THEN** it does not keep a reminder that would only fail later when due

### Requirement: Due effective reminders remain gateway-owned low-priority internal prompt delivery
When the effective reminder becomes due, the gateway SHALL treat delivery of that reminder as gateway-owned internal execution behavior rather than as a new externally visible public request kind.

The public terminal-mutating request-kind set SHALL remain limited to `submit_prompt` and `interrupt`.

Before a due effective reminder starts execution, the gateway SHALL require:

- request admission to be open
- no active terminal-mutating execution
- zero durable public queue depth
- the effective reminder not to be paused

If those conditions are not satisfied when the effective reminder becomes due, the gateway SHALL keep that reminder pending in memory and SHALL retry later instead of dropping the reminder or converting it into durable queued work.

A paused effective reminder SHALL keep its ranking position and SHALL continue blocking lower-ranked reminders until it is resumed, reranked, or removed.

Repeating reminders SHALL maintain at most one pending due occurrence per reminder. Missed intervals during a busy or paused period SHALL NOT produce a catch-up burst of multiple immediate deliveries once the reminder becomes eligible again.

When a due effective reminder uses semantic `prompt` delivery, the gateway SHALL submit exactly that reminder prompt through the existing internal prompt-delivery path.

When a due effective reminder uses `send_keys` delivery, the gateway SHALL submit raw control input through the same exact control-input lane used by gateway send-keys behavior.

For send-keys reminders:

- the gateway SHALL interpret `<[key-name]>` tokens using the same raw control-input grammar used by the gateway send-keys path,
- the reminder SHALL NOT expose a reminder-specific `escape_special_keys` override,
- the gateway SHALL NOT submit `title` or `prompt` text as terminal input for that reminder,
- `ensure_enter=true` SHALL ensure that the delivered control-input sequence ends with exactly one trailing Enter,
- `ensure_enter=false` SHALL preserve the supplied sequence exactly.

#### Scenario: Busy gateway defers a due effective reminder
- **WHEN** the effective reminder becomes due while request admission is blocked, active execution is running, or durable public queue depth is non-zero
- **THEN** the gateway does not start that reminder immediately
- **AND THEN** the effective reminder remains pending in memory until a later safe execution opportunity

#### Scenario: Paused effective reminder blocks lower-ranked due reminders
- **WHEN** the effective reminder is paused and one or more lower-ranked reminders are already due
- **THEN** the gateway does not submit the paused reminder delivery
- **AND THEN** it also does not submit the lower-ranked reminder deliveries while the paused effective reminder still owns the ranking slot

#### Scenario: Due reminder does not expand the public request-kind set
- **WHEN** an effective reminder is delivered after becoming due
- **THEN** that delivery happens through gateway-owned internal behavior rather than a new public `POST /v1/requests` kind
- **AND THEN** the public terminal-mutating request kinds remain exactly `submit_prompt` and `interrupt`

#### Scenario: Send-keys reminder delivers raw control input without title or prompt text
- **WHEN** a due effective reminder uses `send_keys`
- **THEN** the gateway submits the reminder's control-input sequence through the raw control-input lane
- **AND THEN** it does not synthesize `title` or semantic `prompt` text into that terminal input

#### Scenario: Send-keys reminder with ensure-enter true ends with one trailing Enter
- **WHEN** a due effective reminder uses `send_keys` with `ensure_enter=true`
- **THEN** the gateway delivers a control-input sequence that ends with one trailing Enter
- **AND THEN** it does not deliver two trailing Enter presses when the caller already supplied `<[Enter]>`

#### Scenario: Send-keys reminder with ensure-enter false preserves exact sequence
- **WHEN** a due effective reminder uses `send_keys` with `ensure_enter=false`
- **THEN** the gateway delivers the supplied control-input sequence exactly
- **AND THEN** it does not append an implicit Enter

### Requirement: Gateway headless prompt surfaces accept request-scoped execution overrides
For native headless gateway targets, both semantic gateway prompt surfaces SHALL accept an optional request-scoped `execution.model` object:

- `POST /v1/control/prompt`
- `POST /v1/requests` with `kind = submit_prompt`

That `execution.model` object SHALL use the same normalized unified model-selection shape as Houmao launch-owned model configuration.

For native headless targets, the gateway SHALL treat `execution` and `chat_session` as orthogonal controls:

- `chat_session` selects conversation continuity
- `execution.model` selects model and reasoning for the accepted prompt

When both fields are present, the gateway SHALL preserve both through prompt admission and headless execution.

The request-scoped execution override SHALL apply only to the accepted prompt being dispatched or dequeued.

The gateway SHALL NOT store execution state inside `chat_session.current`, `chat_session.startup_default`, or `chat_session.next_prompt_override`.

For TUI-backed targets, any supplied `execution` override on either semantic prompt surface SHALL be rejected with validation semantics rather than ignored.

#### Scenario: Headless direct prompt control accepts execution and chat-session together
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target
- **AND WHEN** the request includes `chat_session.mode = current` and `execution.model.reasoning.level = 4`
- **THEN** the gateway preserves the explicit current-session selector for conversation continuity
- **AND THEN** the gateway applies reasoning level `4` only to that accepted prompt execution

#### Scenario: Headless queued prompt submission accepts the same execution override contract
- **WHEN** a caller submits `POST /v1/requests` with `kind = submit_prompt` for a native headless gateway target
- **AND WHEN** the request payload includes `execution.model.name = "gpt-5.4-mini"`
- **THEN** the gateway accepts that queued semantic prompt request using the same execution-override contract as direct prompt control
- **AND THEN** the later dequeued headless prompt uses `gpt-5.4-mini` only for that queued request

#### Scenario: TUI direct prompt control rejects execution override
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target
- **AND WHEN** the request includes `execution.model.name = "gpt-5.4-mini"`
- **THEN** the gateway rejects that request with validation semantics
- **AND THEN** it does not silently ignore the execution override and pretend that prompt control succeeded

#### Scenario: TUI queued prompt submission rejects execution override
- **WHEN** a caller submits `POST /v1/requests` with `kind = submit_prompt` for a TUI-backed gateway target
- **AND WHEN** the request payload includes `execution.model.reasoning.level = 2`
- **THEN** the gateway rejects that request with validation semantics
- **AND THEN** it does not silently queue a TUI prompt while dropping the requested execution override

### Requirement: Gateway attach applies configurable TUI tracking timings
The gateway companion SHALL accept optional gateway-owned TUI tracking timing configuration when attaching to a gateway-capable TUI-backed managed session.

The timing configuration SHALL include:

- watch poll interval seconds
- readiness stability threshold seconds
- completion stability seconds
- unknown-to-stalled timeout seconds
- stale-active recovery seconds
- final stable-active recovery seconds

When a timing value is omitted, the gateway attach flow SHALL preserve the existing default or previously persisted desired value for that field.

When a timing value is supplied, the gateway attach flow SHALL validate that it is greater than zero before starting the gateway companion.

The gateway companion SHALL apply the resolved timing values to its gateway-owned `SingleSessionTrackingRuntime` and underlying live TUI tracker.

The gateway attach flow SHALL persist the resolved timing configuration in gateway desired configuration so later attach or restart flows for the same gateway root reuse the selected values unless a stronger explicit override is supplied.

The gateway reset-context wait and poll constants SHALL remain unaffected by this timing configuration.

#### Scenario: Explicit attach timings configure gateway-owned TUI tracking
- **WHEN** an operator attaches a gateway to a TUI-backed managed session with explicit gateway TUI timing overrides
- **THEN** the gateway service starts its TUI tracking runtime with those resolved timing values
- **AND THEN** the gateway-owned TUI state lifecycle metadata reflects the configured completion stability, unknown-to-stalled, stale-active recovery, and final stable-active recovery values

#### Scenario: Later attach reuses persisted gateway TUI timings
- **WHEN** a gateway attach succeeds with explicit gateway TUI timing overrides
- **AND WHEN** the same gateway root is attached again without explicit timing overrides
- **THEN** the later attach reuses the persisted desired timing values for gateway-owned TUI tracking

#### Scenario: Invalid gateway TUI timing value is rejected before attach
- **WHEN** a gateway attach request supplies a gateway TUI timing value less than or equal to zero
- **THEN** the attach request fails before starting or reusing the gateway service process
- **AND THEN** the failure identifies the invalid timing field

#### Scenario: Gateway reset-context timing remains separate
- **WHEN** a gateway is attached with gateway TUI tracking timing overrides
- **THEN** those overrides affect continuous TUI tracking, stale-active recovery, and final stable-active recovery
- **AND THEN** they do not change the gateway reset-context wait or reset-context polling constants

### Requirement: Gateway operator-origin post defaults to operator mailbox replies
`POST /v1/mail/offline/post` SHALL default omitted `reply_policy` fields to `operator_mailbox`.

The gateway mailbox post request model SHALL continue to accept explicit `reply_policy` values of `none` and `operator_mailbox`.

When `reply_policy` is omitted or set to `operator_mailbox`, the created operator-origin message SHALL record reply-enabled policy metadata and route replies to `HOUMAO-operator@houmao.localhost`.

When `reply_policy` is explicitly set to `none`, the created operator-origin message SHALL remain no-reply and later replies against that message SHALL fail explicitly.

Pair-managed mail-post proxy request models that inherit the live gateway mailbox post model SHALL preserve this same omitted-field default.

#### Scenario: Direct gateway post omitted policy creates a reply-enabled message
- **WHEN** a caller posts to `/v1/mail/offline/post` with subject and body but without `reply_policy`
- **THEN** the gateway creates an operator-origin message with reply policy `operator_mailbox`
- **AND THEN** a later `/v1/mail/offline/reply` against that message is accepted and routed to `HOUMAO-operator@houmao.localhost`

#### Scenario: Direct gateway explicit no-reply policy is honored
- **WHEN** a caller posts to `/v1/mail/offline/post` with `reply_policy` set to `none`
- **THEN** the gateway creates an operator-origin message with no-reply policy metadata
- **AND THEN** a later `/v1/mail/offline/reply` against that message fails explicitly

#### Scenario: Pair-managed proxy preserves gateway post default
- **WHEN** a pair-managed caller posts operator-origin mail without `reply_policy`
- **THEN** the pair-managed proxy forwards a request that resolves to the gateway's `operator_mailbox` default
- **AND THEN** the resulting message has the same reply-enabled behavior as direct `/v1/mail/offline/post`

### Requirement: Shared gateway mailbox facade exposes lifecycle routes
The shared mailbox facade SHALL expose private `GET /v1/mail/status` as a summary of both optional bindings and the derived canonical mail identity. Mailbox-disabled agents SHALL receive a normal empty-binding summary.

The gateway SHALL expose channel-selected lifecycle routes under `/v1/mail/{channel}/` for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`, where `channel` is `offline` or `online`. The former unqualified lifecycle routes SHALL NOT infer a channel from the canonical mail identity.

List SHALL return triage metadata without marking read. Peek SHALL return selected content without changing read state. Read SHALL return content and mark read. Mark SHALL support recipient-local read/answered state. Move SHALL update supported boxes. Archive SHALL close inbox work through the selected backend.

All lifecycle requests SHALL identify their expected binding ID, obtained from status or current round context, and use runtime-owned authority and scoped references. A replaced binding SHALL fail explicitly even for send/post requests without a message reference. Unsupported operations, absent bindings, and backend failures SHALL be explicit. Callers SHALL NOT need filesystem indexes, mailbox scripts, or provider-native objects. Ordinary mail operations SHALL use private route admission under the live roster. Operator-origin post and mailbox binding controls SHALL use the admin route class.

#### Scenario: Peek does not mutate read state through the gateway
- **WHEN** a caller peeks through the selected channel using a matching scoped reference
- **THEN** it receives that message's content without changing recipient read state

#### Scenario: Read mutates read state through the gateway
- **WHEN** a caller reads through the selected channel using a matching scoped reference
- **THEN** it receives that message's content and read state becomes true for that mailbox owner

#### Scenario: Archive shortcut remains available
- **WHEN** a caller archives selected references through their matching channel
- **THEN** the selected backend reports them archived and no longer open inbox work

#### Scenario: Channel omission does not use canonical precedence
- **WHEN** a caller uses an unqualified lifecycle operation without selecting a channel
- **THEN** the request fails explicitly instead of selecting the preferred online address

#### Scenario: Empty status remains readable
- **WHEN** an agent has no offline or online binding
- **THEN** summary status reports both slots absent and no canonical mail identity
- **AND THEN** ordinary core status and control remain available

#### Scenario: A new send pins its intended mailbox
- **WHEN** an account is replaced after a caller observes its binding ID but before a send begins
- **THEN** the send fails with a binding conflict
- **AND THEN** it is not submitted from the replacement account

#### Scenario: Authenticated remote admin uses both mail channels

- **WHEN** an authenticated admin uses the explicit offline or online lifecycle route with a current expected binding ID
- **THEN** supported ordinary operations follow the same channel, reference, pagination, and mailbox-state semantics as local access
- **AND** the client needs no shared runtime filesystem

#### Scenario: Remote mailbox binding changes before delivery

- **WHEN** a remote request's expected binding no longer identifies the selected owner mailbox
- **THEN** the operation reports the existing scope conflict without delivery from the replacement binding

#### Scenario: Anonymous caller uses ordinary mail with an empty roster

- **WHEN** an unsigned caller accesses an enabled mailbox operation with a current binding ID while the roster is valid and empty
- **THEN** the gateway applies normal channel, reference, and delivery checks with anonymous caller provenance

### Requirement: Gateway reply marks the parent message answered
When a channel-selected gateway reply succeeds, the adapter SHALL mark the parent message `answered=true` and `read=true` for the owning mailbox. Reply SHALL preserve originating channel and binding scope and SHALL NOT archive the parent message.

#### Scenario: Gateway reply acknowledges without closing the mail
- **WHEN** a caller replies through the matching channel and binding
- **THEN** the parent becomes read and answered for that owner
- **AND THEN** it remains open inbox work until archive or a closing move succeeds

### Requirement: Gateway exposes managed memory memo and page endpoints
The live gateway SHALL expose HTTP endpoints for managed memory inspection and memo/page operations.

The gateway memory surface SHALL include:
- a memory summary endpoint that reports memory root, memo file, and pages directory,
- memo read, replace, and append endpoints for the fixed `houmao-memo.md` file,
- page tree, read, write, append, delete, and path-resolution endpoints.

The gateway SHALL NOT expose `scratch` or `persist` lane identifiers on this surface.

The gateway SHALL NOT expose a memory reindex route or action.

#### Scenario: Gateway memory summary reports memo-pages paths
- **WHEN** a live gateway is attached to managed agent `researcher`
- **THEN** the memory summary returns the memory root
- **AND THEN** it returns the memo file path
- **AND THEN** it returns the pages directory
- **AND THEN** it does not return a scratch directory or persist directory

#### Scenario: Gateway rejects lane-style request
- **WHEN** a live gateway receives a workspace lane request for lane `scratch`
- **THEN** the request fails before touching the filesystem
- **AND THEN** the response identifies the lane workspace surface as unsupported

#### Scenario: Gateway does not expose reindex
- **WHEN** a caller uses the supported gateway memory API
- **THEN** there is no supported route for rebuilding a memo page index

### Requirement: Gateway memory endpoints enforce page containment
Gateway page file and path-resolution operations SHALL accept relative page paths only and SHALL verify that each resolved target remains within the managed pages directory.

Gateway page file and path-resolution operations SHALL reject absolute paths, parent traversal, symlink escapes, and content containing NUL bytes where content is supplied.

Gateway memo operations SHALL operate only on the resolved fixed memo file and SHALL NOT accept arbitrary memory-root target paths.

Gateway page operations SHALL NOT mutate `houmao-memo.md`.

#### Scenario: Gateway rejects page symlink escape
- **WHEN** the pages directory contains a symlink whose target resolves outside the pages directory
- **AND WHEN** a gateway memory read request addresses that symlink
- **THEN** the gateway rejects the request
- **AND THEN** it does not read the target outside the pages directory

#### Scenario: Gateway page write leaves memo unchanged
- **WHEN** a gateway memory page write request is accepted for page `operator-rules.md`
- **THEN** the gateway writes to the contained page path
- **AND THEN** it does not update `houmao-memo.md`

### Requirement: Gateway resolves memory page paths
The live gateway memory API SHALL expose a contained page path-resolution operation.

The response SHALL include the page-relative path, the memo-relative link string, the absolute filesystem path, existence state, and existing path kind when available.

The gateway SHALL reject path-resolution inputs that fail the managed page containment rules.

#### Scenario: Gateway resolves a contained future page
- **WHEN** a live gateway receives a path-resolution request for `notes/run.md`
- **AND WHEN** the path is contained under `pages/`
- **THEN** the gateway returns the absolute path for that page under the managed pages directory
- **AND THEN** the gateway returns `relative_link: pages/notes/run.md`

#### Scenario: Gateway rejects path escape resolution
- **WHEN** a live gateway receives a path-resolution request for `../secrets.md`
- **THEN** the gateway rejects the request
- **AND THEN** the gateway does not return an absolute escaped path

### Requirement: Gateway durable storage is current-schema only
The gateway SHALL create current durable queue, notifier, and audit SQLite schemas when a gateway root is new.

When an existing gateway root contains durable SQLite state whose schema is older than the current implementation requires, Houmao SHALL reject that gateway root explicitly and direct the operator to start with a fresh runtime session or gateway root. Houmao SHALL NOT apply in-place SQLite schema upgrades to gateway durable storage.

#### Scenario: Fresh gateway root creates current queue schema
- **WHEN** a runtime session starts with a fresh gateway root
- **THEN** the gateway creates the current durable queue, notifier, and audit tables needed by the current implementation
- **AND THEN** no old gateway schema upgrade path is executed

#### Scenario: Older gateway queue schema is rejected
- **WHEN** a gateway opens existing durable SQLite state that is missing required current queue, notifier, or audit schema shape
- **THEN** gateway startup or state access fails explicitly before mutating that SQLite database
- **AND THEN** the diagnostic directs the operator to recreate the affected runtime session or gateway root

#### Scenario: Notifier table is not upgraded in place
- **WHEN** an existing gateway notifier table lacks a current required column such as notifier mode
- **THEN** Houmao rejects the gateway root as incompatible current gateway state
- **AND THEN** it does not add the missing column through `ALTER TABLE`

### Requirement: Live gateway HTTP clients bypass ambient proxies by default
The live gateway HTTP client SHALL connect directly to its explicit remote base URL or resolved owner-local gateway listener by default and SHALL NOT use ambient proxy environment variables such as `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, or their lowercase variants for gateway requests.

This direct-by-default policy SHALL apply consistently to all requests made through the shared gateway client, including health, endpoint discovery, challenge and key operations, status, public notifications and prompts, request submission, prompt control, TUI control, reminder, mail, mail-notifier, and memory calls.

The direct-by-default policy SHALL NOT require mutating process-wide `NO_PROXY` or `no_proxy` values.

When resolving an owner-local listener whose bind host is `0.0.0.0`, the client SHALL connect through `127.0.0.1` while applying the same proxy policy. An explicit remote base URL SHALL retain its configured origin and path prefix and SHALL NOT be rewritten as caller-local loopback.

#### Scenario: Gateway health bypasses proxy-contaminated environments by default
- **WHEN** a live gateway listener is reachable on `127.0.0.1:<port>`
- **AND WHEN** the caller environment defines `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **AND WHEN** the caller environment does not define loopback `NO_PROXY` or `no_proxy`
- **THEN** a gateway client health request reaches the live gateway listener directly
- **AND THEN** the request does not fail solely because the configured proxy cannot reach or forward the loopback listener

#### Scenario: Gateway proxy bypass is shared across gateway client calls
- **WHEN** a caller uses the shared gateway client for status, request submission, control, reminder, mail, notifier, or memory operations
- **AND WHEN** the caller environment contains ambient proxy variables
- **THEN** those gateway client requests use the same direct-by-default proxy policy as health checks
- **AND THEN** each operation's behavior is not dependent on process-wide `NO_PROXY` mutation

#### Scenario: Explicit remote endpoint remains remote

- **WHEN** a client is configured with an advertised HTTPS base URL containing an agent-specific path prefix
- **THEN** requests use that origin and prefix with the existing direct-by-default proxy policy
- **AND** wildcard owner-listener metadata does not replace it with caller-local loopback

### Requirement: Gateway client proxy use requires an explicit environment opt-in
The live gateway HTTP client SHALL respect ambient proxy environment variables only when `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1` is present in the process environment at gateway client construction time.

When `HOUMAO_GATEWAY_RESPECT_PROXY_ENV` is absent or has any value other than `1`, the gateway client SHALL use direct-by-default behavior.

When proxy-respecting mode is enabled, the gateway client SHALL use the standard Python HTTP proxy handling for the caller environment, including any caller-provided `NO_PROXY` or `no_proxy` values.

The gateway client SHALL NOT persist this proxy policy decision in gateway manifests, gateway status, runtime session manifests, registry records, or durable gateway state.

#### Scenario: Explicit opt-in respects caller proxy settings
- **WHEN** the caller constructs a gateway client with `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1`
- **AND WHEN** the caller environment defines proxy variables
- **THEN** gateway client requests use normal environment proxy handling
- **AND THEN** caller-provided `NO_PROXY` or `no_proxy` values influence proxy bypass according to the standard HTTP client behavior

#### Scenario: Non-one values keep direct gateway behavior
- **WHEN** the caller constructs a gateway client with `HOUMAO_GATEWAY_RESPECT_PROXY_ENV` absent, empty, or set to a value other than `1`
- **THEN** gateway client requests bypass ambient proxy variables
- **AND THEN** the gateway client does not mutate `NO_PROXY` or `no_proxy`

### Requirement: Gateway attach readiness timeouts include the last health probe diagnostic
When gateway attach observes a published listener but health readiness does not succeed before the attach deadline, the attach error SHALL include the target listener host and port.

If at least one health probe failed with a gateway HTTP error before the deadline, the attach error SHALL also include the last observed health probe error detail.

The attach flow SHALL continue using the gateway health endpoint as the authoritative readiness signal; diagnostic files and last-probe details SHALL NOT replace successful health readiness.

#### Scenario: Timeout reports the last health probe error
- **WHEN** gateway attach starts a gateway instance and discovers its listener
- **AND WHEN** every health probe fails until the readiness deadline
- **THEN** the attach result reports that health readiness timed out for the listener host and port
- **AND THEN** the attach result includes the last health probe error detail

#### Scenario: Health success remains the readiness authority
- **WHEN** gateway attach starts a gateway instance and discovers its listener
- **AND WHEN** a health probe returns the expected gateway protocol version before the readiness deadline
- **THEN** gateway attach treats the gateway as ready
- **AND THEN** it does not require separate file-state diagnostics to prove readiness

### Requirement: Gateway clean-context recovery remains explicit or policy-selected
Gateway prompt control SHALL continue to treat recoverable degraded chat context as compatible with ordinary current-context prompt delivery when the target otherwise satisfies the prompt-ready contract.

Clean-context prompt delivery SHALL occur only when one of the following is true:

- the caller explicitly requests clean context through a supported prompt-control chat-session selector,
- a gateway-owned automation policy explicitly selects clean-context recovery for a recognized degraded compaction diagnostic.

For TUI-backed Codex targets, supported clean-context delivery SHALL use the tool-appropriate reset signal and wait for prompt-ready posture before sending the semantic prompt.

For native headless targets, supported clean-context delivery SHALL use the explicit fresh provider-chat selection where that backend supports it.

Recoverable degraded context, generic current-error diagnostics, or historical compact/server text SHALL NOT by themselves select clean-context delivery.

#### Scenario: Ordinary degraded prompt still uses current context
- **GIVEN** a TUI-backed gateway target is prompt-ready with recoverable degraded chat context
- **WHEN** a caller submits direct prompt control without a clean-context selector
- **THEN** the gateway sends the caller's prompt through ordinary current-context prompt delivery
- **AND THEN** it does not first clear context solely because degraded context is present

#### Scenario: Explicit selector still requests clean context
- **GIVEN** a gateway target supports clean-context prompt control
- **WHEN** a caller submits a prompt with an explicit fresh chat-session selector
- **THEN** the gateway uses the supported clean-context workflow for that target
- **AND THEN** the caller's semantic prompt is sent only after clean-context selection or reset succeeds

#### Scenario: Notifier policy can select clean context
- **GIVEN** a gateway-owned mail-notifier policy explicitly selects clean-context recovery for a recognized degraded compaction diagnostic
- **AND GIVEN** the target supports clean-context prompt delivery
- **WHEN** the notifier submits its semantic mailbox notification prompt
- **THEN** the gateway uses clean-context prompt delivery because the notifier policy selected it
- **AND THEN** the same degraded diagnostic would not have selected clean context without that policy

#### Scenario: Generic degraded evidence does not select clean context
- **GIVEN** a gateway target is prompt-ready with current-error or degraded diagnostic evidence that is not a recognized compaction diagnostic for the owning CLI tool
- **WHEN** ordinary prompt control or notifier prompt delivery occurs without an explicit clean-context selector or policy match
- **THEN** the gateway does not run a reset-then-send workflow
- **AND THEN** it does not force a native headless fresh-chat selector solely from that generic evidence

### Requirement: Gateway maintains active-thread destination state
The gateway SHALL maintain volatile Houmao AG-UI destination state containing active-thread and last-sent-thread.

The active-thread state SHALL start empty when the gateway process starts.

The last-sent-thread state SHALL start empty when the gateway process starts.

The gateway SHALL expose Houmao extension routes to read destination state, read active-thread, set active-thread, and clear active-thread.

The active-thread set operation SHALL require a non-empty `threadId` string.

The destination state SHALL be a Houmao gateway extension and SHALL NOT be described as part of the AG-UI core standard.

#### Scenario: Gateway starts with empty active destination state
- **WHEN** a gateway process starts
- **THEN** active-thread is empty
- **AND THEN** last-sent-thread is empty

#### Scenario: GUI sets active thread
- **WHEN** a workbench client sets active-thread to `agent-1-thread`
- **THEN** the gateway stores `agent-1-thread` as the current active AG-UI thread
- **AND THEN** later reads report active state for `agent-1-thread`

#### Scenario: Empty active thread is rejected
- **WHEN** a caller attempts to set active-thread to an empty or blank string
- **THEN** the gateway rejects the request
- **AND THEN** the previous active-thread state is not replaced by a blank value

### Requirement: Gateway conditionally clears active-thread
The gateway SHALL support clearing active-thread.

When a clear request includes an expected thread id, the gateway SHALL clear active-thread only if the current active-thread matches that expected thread id.

When a clear request includes an expected thread id that does not match the current active-thread, the gateway SHALL leave active-thread unchanged and return the current active-thread state.

Clearing active-thread SHALL NOT clear last-sent-thread.

#### Scenario: Matching expected thread clears active state
- **WHEN** active-thread is `alpha-thread`
- **AND WHEN** a caller clears active-thread with expected thread id `alpha-thread`
- **THEN** the gateway clears active-thread
- **AND THEN** last-sent-thread is unchanged

#### Scenario: Stale expected thread does not clear active state
- **WHEN** active-thread is `beta-thread`
- **AND WHEN** a stale caller clears active-thread with expected thread id `alpha-thread`
- **THEN** the gateway keeps active-thread set to `beta-thread`

### Requirement: Gateway publish resolves destinations through explicit route, active-thread, then default sink
The gateway SHALL resolve AG-UI event publish routing in deterministic priority order.

Destination specified by the publish request or event batch SHALL take priority over gateway fallback state.

When no destination is specified by the publish request or event batch, the gateway SHALL use active-thread if it exists.

When no destination is specified and active-thread is empty, the gateway SHALL send the batch to a Houmao-defined default sink.

The gateway SHALL NOT use last-sent-thread as a publish fallback destination.

The default sink thread name SHALL NOT be returned as an agent-targetable route.

The current default sink behavior SHALL accept the valid batch, write a gateway log entry with safe routing metadata, perform no GUI fan-out, and return a warning that the default sink was used because no destination was available.

#### Scenario: Explicit thread destination wins over active thread
- **WHEN** a caller publishes an AG-UI event batch with an explicit `threadId`
- **AND WHEN** the gateway has a different active-thread value
- **THEN** the gateway routes the batch to the explicit thread id

#### Scenario: Active thread is used for omitted route
- **WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **AND WHEN** active-thread is `agent-active-thread`
- **THEN** the gateway routes the batch to `agent-active-thread`
- **AND THEN** the publish response reports accepted and delivered counts according to live subscribers

#### Scenario: Last-sent thread is not used as fallback
- **WHEN** active-thread is empty
- **AND WHEN** last-sent-thread is `agent-last-sent-thread`
- **AND WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **THEN** the gateway sends the batch to the default sink

#### Scenario: Default sink is used when active thread is empty
- **WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **AND WHEN** active-thread is empty
- **THEN** the gateway sends the batch to the default sink
- **AND THEN** the response includes a warning that no destination was available

### Requirement: Gateway keeps last-sent-thread as bookkeeping only
The gateway SHALL refresh last-sent-thread after an AG-UI publish resolves to a concrete non-sink destination and the gateway sends the batch through its normal publish path.

When a publish uses a message-specified destination, the gateway SHALL set last-sent-thread to that concrete destination when known.

When a publish uses active-thread fallback, the gateway SHALL set last-sent-thread to that active thread after the publish is sent.

When a publish falls through to the default sink, the gateway SHALL NOT set last-sent-thread to the sink.

Last-sent-thread SHALL NOT participate in future destination fallback decisions.

#### Scenario: Active-thread publish refreshes last-sent
- **WHEN** active-thread is `agent-active-thread`
- **AND WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **THEN** the gateway routes the batch to `agent-active-thread`
- **AND THEN** last-sent-thread becomes `agent-active-thread`

#### Scenario: Default sink does not refresh last-sent
- **WHEN** active-thread is empty
- **AND WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **THEN** the gateway uses the default sink
- **AND THEN** last-sent-thread remains unchanged

### Requirement: Gateway direct prompt control uses explicit admission policies

Gateway direct prompt control through `POST /v1/control/prompt` SHALL accept `admission_policy = ready_only | if_no_pending | always` and SHALL default omitted policy to `ready_only`.

For a terminal TUI-backed target, `ready_only` SHALL require the existing stable prompt-ready contract and `surface.pending_input=no`. It SHALL reject busy, pending, or pending-unknown observations.

For a terminal TUI-backed target, `if_no_pending` SHALL ignore prompt-readiness and busy posture, dispatch only when the latest gateway-owned tracked snapshot reports `surface.pending_input=no`, reject `yes` with `error_code=pending_input`, and reject `unknown` with `error_code=pending_input_unknown`.

For a terminal TUI-backed target, `always` SHALL bypass tracked readiness and pending-input checks. Every policy SHALL still reject unavailable, detached, reconciliation-blocked, invalid-selector, incompatible-target, and unsupported-target requests.

When the addressed terminal TUI session has an active hook observation channel, `ready_only` SHALL additionally require that the merged hook posture reports neither an active nor a blocked turn, and `if_no_pending` SHALL additionally require that the hook posture does not report blocked. Hook-reported background work SHALL NOT by itself close any policy, and `always` SHALL remain unaffected by hook posture.

A hook channel that is unavailable, stale, disabled, untrusted, or errored SHALL NOT add refusal reasons: admission SHALL evaluate exactly the TUI-only facts above. Admission decision records SHALL include the hook channel state, the hook posture facts, and any conflict reasons used in the decision.

For terminal TUI targets, the admission decision SHALL be observational. The gateway SHALL NOT reserve the observed no-pending state or promise atomic compare-and-submit behavior across concurrent requests. Two calls that both observe `pending_input=no` MAY both dispatch before the provider TUI repaints.

Non-default admission policies SHALL be rejected for native headless targets, and native headless prompt control SHALL continue to reject overlapping active execution. Interactive `chat_session.mode=new` SHALL require `ready_only` because reset-then-send depends on stable prompt readiness.

Prompt submission SHALL continue to arm explicit-input tracking where applicable, but the gateway SHALL NOT synthesize `surface.pending_input` from its dispatch, event, reminder, notifier, raw-input, or durable-request state.

For a Web interactive target, `ready_only` SHALL require native idle, unblocked, no-pending state; `if_no_pending` SHALL permit busy state only with an unblocked agent and empty native inbox; `always` SHALL bypass native readiness and pending-input checks. Each policy SHALL still verify the exact live host/agent incarnation and structural availability. Its native check and input insertion SHALL be atomic after asynchronous preparation. These policies authorize only the requested operation, not automatic prompt resend or cold-session activation.

#### Scenario: Default policy sends to a stable ready TUI with no pending input

- **WHEN** a caller omits `admission_policy`
- **AND WHEN** the addressed TUI satisfies the stable prompt-ready contract and reports `surface.pending_input=no`
- **THEN** the gateway dispatches the prompt under `ready_only`
- **AND THEN** the success response identifies `admission_policy=ready_only`

#### Scenario: Ready-only backs off while the TUI is busy

- **WHEN** a caller selects `ready_only` while the addressed TUI does not satisfy the stable prompt-ready contract
- **THEN** the gateway refuses the prompt with `error_code=not_ready`
- **AND THEN** it does not submit the prompt to the provider CLI

#### Scenario: Ready-only backs off when hooks report an active or blocked turn

- **WHEN** a caller selects `ready_only` for a session whose TUI satisfies the stable prompt-ready contract with `surface.pending_input=no`
- **AND WHEN** the active hook observation channel reports the turn active or blocked
- **THEN** the gateway refuses the prompt with `error_code=not_ready`
- **AND THEN** the refusal record carries the hook posture facts

#### Scenario: If-no-pending submits while busy when the queue is visibly empty

- **WHEN** a caller selects `if_no_pending` while the TUI is busy and the latest tracked snapshot reports `surface.pending_input=no`
- **THEN** the gateway dispatches the prompt to the provider CLI
- **AND THEN** it does not require `turn.phase=ready` or `surface.ready_posture=yes`

#### Scenario: If-no-pending backs off from an existing provider-native queue

- **WHEN** a caller selects `if_no_pending` and the latest tracked snapshot reports `surface.pending_input=yes`
- **THEN** the gateway refuses the prompt with `error_code=pending_input`
- **AND THEN** it does not add that prompt to the provider CLI queue

#### Scenario: If-no-pending backs off while hooks report blocked

- **WHEN** a caller selects `if_no_pending` and the latest tracked snapshot reports `surface.pending_input=no`
- **AND WHEN** the active hook observation channel reports the turn blocked on a permission request
- **THEN** the gateway refuses the prompt with `error_code=not_ready`
- **AND THEN** it does not dispatch the prompt

#### Scenario: Degraded hook channel adds no refusal reasons

- **WHEN** a caller selects `ready_only` or `if_no_pending` for a session whose hook channel is unavailable, stale, disabled, untrusted, or errored
- **AND WHEN** the TUI-only facts would admit the prompt
- **THEN** the gateway admits the prompt exactly as it would without the channel
- **AND THEN** the decision record carries the hook channel state without adding refusal reasons

#### Scenario: If-no-pending treats uncertainty conservatively

- **WHEN** a caller selects `if_no_pending` and the latest tracked snapshot reports `surface.pending_input=unknown`
- **THEN** the gateway refuses the prompt with `error_code=pending_input_unknown`
- **AND THEN** it does not reinterpret unknown as an empty provider queue

#### Scenario: Always submits despite visible pending input

- **WHEN** a caller selects `always` for an attached compatible TUI whose latest tracked snapshot reports `surface.pending_input=yes`
- **THEN** the gateway dispatches the prompt
- **AND THEN** structural availability and compatibility failures remain enforceable

#### Scenario: Closely spaced conditional submissions may both dispatch before repaint

- **WHEN** two `if_no_pending` calls for a terminal TUI target independently observe the same latest snapshot with `surface.pending_input=no`
- **THEN** both calls may dispatch before a later TUI capture reports the provider queue
- **AND THEN** the gateway does not claim an exactly-one reservation guarantee

#### Scenario: Later conditional submission reacts to observed pending state

- **WHEN** earlier submissions have reached the provider CLI and a later tracked snapshot reports `surface.pending_input=yes`
- **THEN** a later `if_no_pending` call backs off
- **AND THEN** a later `always` call may still dispatch

#### Scenario: Admission decision records carry hook facts

- **WHEN** the gateway accepts or refuses a prompt for a session with an active hook observation channel
- **THEN** the durable decision record includes the hook channel state, hook turn posture, hook terminal result, and any conflict reasons used

#### Scenario: Non-default policy is rejected for headless prompt control

- **WHEN** a caller selects `if_no_pending` or `always` for a native headless target
- **THEN** the gateway rejects the policy with validation semantics
- **AND THEN** it does not invent provider-native pending-input state or start overlapping headless work

#### Scenario: TUI new-session workflow requires ready-only policy

- **WHEN** a TUI direct prompt request combines `chat_session.mode=new` with `if_no_pending` or `always`
- **THEN** the gateway rejects the incompatible request with validation semantics
- **AND THEN** it does not begin a context-reset workflow from a busy or pending posture

#### Scenario: Web Ready-Only Rechecks After Human Input
- **WHEN** a Web request initially observes readiness but a human starts native work before its handoff
- **THEN** the native atomic admission rejects the ready-only request without queueing it

#### Scenario: Web If-No-Pending Explicitly Admits Busy Input
- **WHEN** an operator selects `if_no_pending` for a live unblocked Web agent whose native pending inbox is empty
- **THEN** a busy agent may accept that explicitly requested next-turn input
- **AND THEN** ordinary plugin delivery still uses ready-only admission

#### Scenario: Web Always Preserves Structural Refusals
- **WHEN** a Web `always` request carries a stale execution incarnation
- **THEN** it is refused without activating or targeting a replacement agent

### Requirement: Gateway prompt-control schema and CLI remove binary force behavior

The direct prompt-control request schema SHALL advance to schema version 2, SHALL contain `admission_policy`, and SHALL NOT contain `force`. Success and structured-refusal payloads SHALL report `admission_policy` and SHALL NOT report a boolean `forced` field.

The maintained `houmao-mgr agents single|self ... gateway prompt` commands SHALL expose `--admission-policy ready-only|if-no-pending|always` with `ready-only` as the default and SHALL NOT expose `--force` as an alias or deprecated compatibility flag.

Gateway event and diagnostic records for direct prompt decisions SHALL identify the selected admission policy and the observed readiness/pending facts used by conditional decisions.

#### Scenario: Version-two API accepts an explicit policy

- **WHEN** a caller sends a schema-version-2 direct prompt request with `admission_policy=if_no_pending`
- **THEN** the gateway validates and evaluates that named policy
- **AND THEN** the result or refusal reports the same policy

#### Scenario: Legacy force payload is rejected

- **WHEN** a caller sends a direct prompt-control payload containing `force` or schema version 1
- **THEN** strict request validation rejects the payload
- **AND THEN** the gateway does not translate it into an admission policy

#### Scenario: CLI maps hyphenated policy values to the API enum

- **WHEN** an operator runs `houmao-mgr agents single --agent-name worker gateway prompt --admission-policy if-no-pending --prompt ping`
- **THEN** the CLI sends `admission_policy=if_no_pending` through the selected managed-agent path
- **AND THEN** command output reports the selected policy instead of a forced boolean

#### Scenario: Removed force flag has no shim

- **WHEN** an operator invokes gateway prompt with `--force`
- **THEN** Click rejects the unknown option
- **AND THEN** help output directs current callers only through `--admission-policy`

### Requirement: Gateway exposes bounded finalized usage retrieval

The live gateway SHALL expose `GET /v1/usage` with optional `after` cursor and bounded `limit` inputs. It SHALL return versioned records, stream identity, evidence-based capability, a resumable cursor, and page-continuation state for supported headless and native-observed turns.

#### Scenario: Headless usage page is returned

- **WHEN** a caller queries a headless target with finalized usage
- **THEN** the gateway returns the requested bounded page in finalization order

#### Scenario: Qualified TUI usage page is returned

- **WHEN** a caller queries a TUI target with validated native-log accounting
- **THEN** the gateway returns its finalized records through the same usage page contract

#### Scenario: Polling continues after an empty page

- **WHEN** a caller saves a queryable stream's cursor from an empty page and a record later finalizes
- **THEN** a request after that cursor returns the later record without restarting history

#### Scenario: Invalid pagination input fails validation

- **WHEN** a caller supplies an invalid or wrong-stream cursor or an out-of-bounds limit
- **THEN** the gateway returns HTTP 422 without substituting an unbounded query

### Requirement: Gateway usage capability reflects available accounting evidence

Usage capability SHALL identify validated sources, observed scopes, turn-recording support, and safe limitation reasons. Unsupported sources SHALL NOT produce fabricated records. Existing finalized history SHALL remain readable when current collection becomes degraded or unavailable.

#### Scenario: Unsupported TUI source returns a capability response

- **WHEN** a TUI target has no validated structured accounting source
- **THEN** the gateway returns unavailable accounting capability without fabricated usage or unrelated headless-control errors

#### Scenario: Session-only source does not imply turn support

- **WHEN** a target exposes cumulative session evidence without verified turn association
- **THEN** its capability identifies that limitation and does not claim per-turn token accounting

#### Scenario: Collector failure preserves known records

- **WHEN** the current source becomes unreadable after earlier records were finalized
- **THEN** the gateway returns readable finalized history with degraded collection capability and a safe diagnostic

#### Scenario: Usage storage is incompatible

- **WHEN** the usage store cannot be read because its schema is incompatible or its storage is unavailable
- **THEN** the gateway returns HTTP 503 with safe diagnostics rather than reporting an empty successful history

### Requirement: Gateway manages bound usage collection through its lifecycle

For a qualified attached target, the gateway SHALL start or resume collection against the runtime-session binding, recover missed accounting after restart, and release its collection worker on shutdown. Replacement instances SHALL resume durable progress without duplicate records.

#### Scenario: Gateway restarts during native-log collection

- **WHEN** a gateway restarts after observing part of a bound native log
- **THEN** collection resumes from durable progress and known requests do not receive new charges

#### Scenario: Gateway attaches to a conversation with history

- **WHEN** collection first attaches to an existing provider conversation
- **THEN** it establishes a boundary and does not import earlier usage as new managed work

### Requirement: Gateway usage reads do not mutate or serialize agent execution

`GET /v1/usage` SHALL NOT acquire the terminal-mutation slot, enqueue prompts, interrupt execution, or require an idle agent. Ordinary reads SHALL use bounded finalized history without synchronously scanning provider-log or artifact trees.

#### Scenario: Active agent continues during a history query

- **WHEN** a caller requests usage while a turn is active
- **THEN** previously finalized records remain readable without changing active execution
- **AND THEN** the active turn remains absent from finalized history

### Requirement: Normal Gateway Launches Restore Explicit Plugin Selections

The gateway SHALL accept typed plugin configuration through supported Python launch/attach interfaces and a configuration-file option on maintained gateway attach commands. It SHALL persist resolved selections and credential references, preserving them through foreground and detached launches, capability refresh, and restart.

#### Scenario: Python Caller Configures Plugins at Launch

- **WHEN** a library caller supplies valid plugin selections with gateway auto-attach enabled
- **THEN** the launched gateway resolves those selections in its own interpreter environment
- **AND THEN** the caller does not need process-local registration side effects or source modifications

#### Scenario: Operator Adds Plugins to an Already-Running Agent

- **WHEN** an operator attaches a gateway using `--plugins-config PATH` through a maintained scoped manager command
- **THEN** the selected plugin instances are persisted and loaded by that gateway
- **AND THEN** attaching does not restart or rebuild the agent body

#### Scenario: Later Attach Omits a Plugin Override

- **WHEN** gateway capability is refreshed or a stopped gateway is attached without a plugin selection override
- **THEN** previously persisted selections and references are preserved
- **AND THEN** both same-session foreground and detached execution modes restore them

#### Scenario: Explicit Empty Selection Clears Plugins

- **WHEN** a stopped gateway is attached with an explicit empty plugin mapping
- **THEN** the persisted selection becomes empty and no plugin implementation activates
- **AND THEN** omission remains distinct from an explicit empty selection

#### Scenario: Live Gateway Receives a Different Immutable Configuration

- **WHEN** an attach operation supplies plugin configuration different from a live gateway's active configuration
- **THEN** it returns an explicit restart-required conflict without changing active or persisted selections
- **AND THEN** an equivalent configuration can reuse the live gateway

### Requirement: Plugin Activation Follows Core Listener Initialization

The gateway SHALL coordinate plugin lifecycle with resolved listener binding and core runtime initialization. Core readiness SHALL NOT wait for external plugin service availability. Plugin routes SHALL remain gated until their instance is active, and the same lifecycle contract SHALL apply to normal service execution and supported embedded application construction.

#### Scenario: System-Assigned Listener Is Resolved Before Activation

- **WHEN** a gateway starts on a system-assigned port with configured plugins
- **THEN** core initialization resolves and publishes the actual listener before plugin resources activate
- **AND THEN** plugins receive the resolved listener context when they need it

#### Scenario: External Service Does Not Respond During Startup

- **WHEN** a configured plugin's service is unavailable or its startup deadline expires
- **THEN** core health and operator control remain available
- **AND THEN** the affected instance reports starting, degraded, or failed status as appropriate while custom-route admission remains explicit

#### Scenario: Embedded Host Enters and Exits the Gateway Lifecycle

- **WHEN** a supported embedded host or ASGI test starts and stops the gateway application
- **THEN** configured plugin lifespans enter and exit exactly once under the same lifecycle coordinator
- **AND THEN** workers are not dependent on an otherwise unexecuted CLI-only startup path

### Requirement: Plugin Failure Does Not Replace Core Gateway Health

The gateway SHALL keep core health, status, usage, operator-control, mailbox, and AG-UI surfaces independent of individual plugin health. Missing packages, incompatible definitions, route conflicts, failed initialization, and worker failures SHALL remain visible through host-owned plugin status while unrelated plugins and core facilities continue.

#### Scenario: One Plugin Fails While Another Is Healthy

- **WHEN** one configured plugin fails registration or execution and another configured instance is healthy
- **THEN** the healthy instance continues serving its routes
- **AND THEN** core health, status, usage, and available operator-control operations remain accessible

#### Scenario: Failed Namespace Receives a Custom Request

- **WHEN** a caller addresses a custom endpoint within a known failed instance's namespace
- **THEN** the host returns a safe HTTP 503 without calling failed plugin code
- **AND THEN** the instance's host-owned status remains readable

### Requirement: Plugin Service Operations Respect Gateway Access Policy

Plugin custom routes, credential resolution, workers, and event intake SHALL require valid gateway deployment. A broader listener without validated access configuration SHALL fail before importing plugin code or activating resources. Plugin routes SHALL enforce their declared access class using live policy. Sanitized host-owned status SHALL remain available to admitted callers independently of plugin health.

#### Scenario: All-Interface Listener Has Configured Plugins

- **WHEN** a gateway selects host `0.0.0.0` and plugin selections without validated access configuration
- **THEN** startup is refused before implementation imports, credential resolution, or plugin workers
- **AND** no unauthenticated broader plugin surface is published

#### Scenario: Valid broader listener activates selected plugins

- **WHEN** a broader gateway listener has valid access configuration and valid plugin selections
- **THEN** selected plugins can activate under the normal supervised lifecycle
- **AND** custom routes enforce caller authority while background ordinary events retain owner and readiness guards

### Requirement: Ordinary Plugin Event Refusals Are Immediate

The gateway SHALL attempt plugin-event dispatch only with ready gateway/plugin state, open core admission, idle available body, and applicable readiness, pending-input, and active-hook guards. A failed readiness check SHALL return a retryable error without waiting, caching, queueing, or scheduling the message for later delivery.

#### Scenario: Busy Headless Agent Refuses an Event

- **WHEN** a plugin event arrives while a headless turn is active
- **THEN** the gateway returns HTTP 409 with a retryable readiness error
- **AND THEN** it starts no overlapping turn and stores no pending plugin message

#### Scenario: Ready TUI Still Has Provider Pending Input

- **WHEN** an event targets a TUI whose tracked pending input is `yes` or `unknown`
- **THEN** the gateway returns a retryable readiness error even if the surface otherwise looks ready
- **AND THEN** it does not enqueue the event through the durable request queue

#### Scenario: Active Hook Posture Blocks a Visually Ready TUI

- **WHEN** a TUI surface is stable and ready with no pending input but an active hook channel reports active or blocked work
- **THEN** the event request fails immediately instead of waiting for a different hook posture
- **AND THEN** stale, unavailable, or disabled hook channels add no gates beyond the established TUI-only rules

#### Scenario: Existing Accepted Work Conflicts With Immediate Dispatch

- **WHEN** existing gateway work prevents immediate plugin-event dispatch
- **THEN** the event request returns a retryable conflict and existing work retains its normal scheduling
- **AND THEN** the plugin request does not join that queue or hold the execution lock while waiting

#### Scenario: Readiness Changes Before Dispatch

- **WHEN** initial checks pass but the body becomes inadmissible before dispatch
- **THEN** the original request returns an error and relinquishes its attempt
- **AND THEN** later readiness does not resume that request in the background

#### Scenario: Plugin Dispatch Does Not Add a Queued Request Kind

- **WHEN** a plugin event is dispatched through the immediate semantic path
- **THEN** no queued plugin-event request is created
- **AND THEN** the public request kinds remain `submit_prompt` and `interrupt`

### Requirement: Body Loss During Plugin Dispatch Fails the Original Request

The gateway SHALL keep a plugin event request in flight until dispatch confirmation to its captured body incarnation. Observed body death, restart, replacement, or unconfirmed handoff before response finalization SHALL fail that request. It SHALL NOT return success from a queued acknowledgement or worker start, retain a resend payload, or continue the attempt against a replacement body.

#### Scenario: Body Dies After Gateway Admission but Before Handoff

- **WHEN** an event passes gateway admission and the addressed body dies before confirmed handoff
- **THEN** the original request returns HTTP 503 with a retryable body-unavailable error
- **AND THEN** its payload is discarded rather than cached for the next body

#### Scenario: Body Restarts Under the Same Logical Agent Name

- **WHEN** the body changes execution incarnation during dispatch while its logical agent/session identity remains the same
- **THEN** the original request fails with a retryable target-changed error
- **AND THEN** no surviving callback forwards its message to the replacement body

#### Scenario: Body Loss Is Observed After Handoff but Before Response

- **WHEN** handoff may have occurred but body death or replacement is observed before successful response finalization
- **THEN** the request returns a retryable error with uncertain dispatch outcome
- **AND THEN** the gateway does not claim a known unsent message or perform another attempt

#### Scenario: Headless Worker Starts Before Its Client Handoff

- **WHEN** a local headless worker thread starts but client dispatch has not yet been confirmed
- **THEN** the event request remains in flight within its finite deadline
- **AND THEN** a failed launch or missing confirmation returns an error instead of an early success

#### Scenario: Dispatch Confirmation Times Out

- **WHEN** a live request cannot confirm handoff within its finite deadline
- **THEN** it returns an explicit failure and revokes not-yet-dispatched request work
- **AND THEN** a later callback cannot resume delivery after body recovery

### Requirement: Gateway Recovery Does Not Resend Plugin Messages

Gateway restart SHALL restore plugin selections and service resources without restoring notification payloads or initiating resend. Sender retry SHALL be a new request evaluated against current readiness. A success response SHALL mean confirmed dispatch only; a body failure occurring after that completed response SHALL NOT create a retroactive response or automatic redelivery.

#### Scenario: Body Becomes Ready After a Rejection

- **WHEN** a rejected message's body becomes ready without another sender request
- **THEN** the gateway performs no delivery of that message
- **AND THEN** only an explicit new sender request can start another attempt

#### Scenario: Gateway Restarts After an Interrupted Request

- **WHEN** the gateway restarts after a message request failed or lost its connection
- **THEN** it restores no cached event, pending notification, or resend job
- **AND THEN** the sender retains responsibility for any new attempt

#### Scenario: Sender Retries After Recovery

- **WHEN** the sender retries a failed message after the gateway and current body become ready
- **THEN** the new request independently evaluates readiness and can dispatch
- **AND THEN** the gateway does not combine it with a cached earlier attempt

#### Scenario: Body Dies After a Completed Success Response

- **WHEN** a successful dispatch response has already completed and the body subsequently dies
- **THEN** that completed response cannot be changed retroactively
- **AND THEN** the gateway neither infers completed agent processing nor automatically resends the message

### Requirement: DSH ACP Agents Support Managed Gateway Operations

Runtime-owned DSH ACP agents SHALL support gateway attach, detach, semantic prompt, interruption, status, canonical events, and shared usage access through the persistent service owner. Readiness SHALL reflect the verified ACP connection, bound session, and active execution throughout the service lifetime.

#### Scenario: Gateway Attaches Between DSH Turns
- **WHEN** the managed DSH service owner has an initialized ACP connection and an idle bound session
- **THEN** gateway attach succeeds and exposes the agent's actual idle or unavailable posture

#### Scenario: DSH Work Is Already Active
- **WHEN** an ordinary plugin event arrives while DSH has an active managed turn
- **THEN** the gateway returns an immediate retryable conflict
- **AND THEN** no plugin payload enters a delayed queue or overlapping ACP request

#### Scenario: Gateway reattaches with the service down

- **WHEN** the supervisor exists but its ACP connection was lost
- **THEN** the gateway reports native control unavailable and does not start a replacement provider to answer a read

### Requirement: DSH Immediate Dispatch Is Fenced at Native Handoff

An immediate DSH event attempt SHALL bind its dispatch permission to the captured managed generation and native execution. Native admission evidence SHALL belong to that attempt. Expiry, caller loss before handoff, provider failure, or execution replacement SHALL revoke the attempt and report failure or uncertainty without retaining authority to resend its payload.

#### Scenario: The Driver Starts but DSH Rejects the Prompt
- **WHEN** the helper launches but initialization, session selection, or native prompt admission fails
- **THEN** the gateway returns a dispatch error rather than treating helper process creation as successful handoff

#### Scenario: The Managed Generation Changes Before Input
- **WHEN** an event passes initial checks but its captured execution generation changes before native input is submitted
- **THEN** the attempt fails and its prompt is not sent to the replacement generation

#### Scenario: Provider Failure Follows Native Admission
- **WHEN** DSH admits the prompt but exits or restarts before the pending operation reaches a confirmed terminal result
- **THEN** the pending response or recorded result reports failure or uncertainty
- **AND THEN** neither gateway recovery nor later readiness resends the original prompt

### Requirement: DSH Mail and Plugin Integrations Reuse Core Admission

Mail reminders, CCCC chat, explicit deferred-message consumption, and other plugins targeting a qualified DSH headless, service, or Web agent SHALL use the existing owner-bound semantic dispatch and shared core admission. Adding DSH SHALL NOT create another mailbox identity, bypass delivery selection, or change existing periodic reminder semantics.

#### Scenario: An Eligible Mail Reminder Wakes a DSH Agent
- **WHEN** an existing mailbox notifier finds eligible work while the DSH agent is ready
- **THEN** its notification uses ordinary managed semantic dispatch
- **AND THEN** unchanged inbox work retains the configured periodic reminder behavior

#### Scenario: A Plugin Calls the DSH Agent Through Its Owner
- **WHEN** an enabled owner-bound plugin delivers an event to the DSH gateway
- **THEN** existing plugin ownership, readiness, and execution-generation checks remain in force

#### Scenario: A service is disconnected at dispatch

- **WHEN** an ordinary reminder or plugin wake targets a DSH owner without a verified ACP connection
- **THEN** core admission reports the unavailable target and does not enqueue a later native prompt

### Requirement: DSH Web Ordinary Events Use Native Immediate Admission

Ordinary events targeting DSH Web SHALL use the captured live execution and native ready-only admission. Gateway/plugin health, core admission, native idle/readiness, pending-input state, and native interaction waits SHALL all be satisfied at handoff. Rejection or execution loss SHALL not create a delayed gateway or native delivery.

#### Scenario: Browser Input Wins the Admission Race
- **WHEN** a human starts work after gateway inspection but before an ordinary event's native insertion
- **THEN** the event receives an immediate retryable error and enters neither the native inbox nor the gateway queue

#### Scenario: Provider Replacement Follows Native Admission
- **WHEN** DSH replaces the bound host or agent while an admitted event still has a pending delivery or completion result
- **THEN** that result reports failure or uncertainty
- **AND THEN** the event is not rebound or replayed against the replacement

### Requirement: Web Gateway Observation Uses Structured Native State

A DSH Web gateway SHALL expose current native state and bounded recent state history through Web-specific control surfaces and common status/events. Observation SHALL follow both human and programmatic work without depending on terminal capture or browser DOM inspection. Terminal-only control routes SHALL return explicit unsupported semantics for a Web surface.

#### Scenario: Browser Approval Blocks Native Work
- **WHEN** the shared DSH session waits for a native human approval
- **THEN** gateway state reports the blocked interaction and ordinary prompt admission is closed
- **AND THEN** observing that state neither answers the approval nor marks the gateway itself unhealthy

#### Scenario: Terminal Tracking Is Requested for DSH Web
- **WHEN** a caller requests a terminal-parser state, terminal snapshot history, or raw keys for the Web agent
- **THEN** the gateway returns unsupported-capability information with the supported structured inspection surface

### Requirement: Gateway separates bind local-connect and advertised addresses

The gateway SHALL distinguish its bind address, owner-local connect URL, and explicit advertised remote URL. Live local discovery SHALL retain owner-qualified listener facts. Advertised URLs SHALL be validated non-secret HTTP or HTTPS base URLs under the transport policy. They SHALL NOT be inferred from inbound Host or forwarded headers, or imply a caller-local filesystem or loopback endpoint.

#### Scenario: TLS proxy has a different reachable address

- **WHEN** a gateway binds owner loopback and an operator configures a distinct HTTPS proxy URL
- **THEN** local controls use the owner-local endpoint
- **AND** remote discovery exports the configured HTTPS URL independently of the listener address

#### Scenario: Incoming host header disagrees with configured advertisement

- **WHEN** a request supplies a different Host or forwarded host
- **THEN** it does not change the gateway's advertised endpoint

### Requirement: Public endpoint discovery reports a minimal descriptor

GET /v1/endpoint SHALL return a secret-free descriptor with target and presence identity, protocol, open or key-required admin access, private access requirements, enabled public operations, and the configured advertised URL if present. It SHALL report `private_proof` as `none` when open, `self_or_admin` when keyed, and `unavailable` when the policy is unavailable. Detailed status SHALL require private access.

#### Scenario: Anonymous caller discovers a protected gateway

- **WHEN** a caller reads the endpoint descriptor without credentials
- **THEN** it receives the current access requirements and enabled public operations
- **AND** detailed status, owner-local paths, and roster contents are absent

#### Scenario: The first key is registered after advertisement

- **WHEN** a caller reads the endpoint descriptor after the first-key registration commits
- **THEN** it reports key-required admin access and `private_proof: self_or_admin`

#### Scenario: The roster is valid and empty

- **WHEN** a caller reads the endpoint descriptor with a valid empty roster
- **THEN** it reports open admin access and `private_proof: none`

#### Scenario: Policy is unavailable

- **WHEN** the live gateway cannot read its required access state
- **THEN** it reports unavailable access for both route classes

### Requirement: Public input accepts bounded notifications and prompts

Owner enablement SHALL make both public input routes callable by anyone. POST /v1/messages SHALL accept bounded source_event_id, text, and optional metadata for a notification. POST /v1/public/prompt SHALL accept bounded source_event_id and prompt for a direct request. Both routes SHALL use strict schemas, finite envelope limits, and a bounded admission budget.

#### Scenario: Public input is disabled by default

- **WHEN** an unconfigured gateway starts and receives a public notification or prompt attempt
- **THEN** both public input operations are unavailable
- **AND** health and endpoint discovery still report their public data

#### Scenario: Uncredentialed caller sends a notification

- **WHEN** a caller sends a valid notice about a message to an enabled gateway and a ready body
- **THEN** the gateway hands off a notification that the agent can act on through its existing access

#### Scenario: Uncredentialed caller submits a prompt

- **WHEN** a caller submits a valid public prompt to an enabled gateway and a ready body
- **THEN** the gateway can start an ordinary turn for the current agent

#### Scenario: Public input exceeds a limit

- **WHEN** public input exceeds its supported envelope or admission limit
- **THEN** the gateway refuses it without starting body work
- **AND** exhausting the admission budget returns HTTP 429

### Requirement: The gateway labels public input and preserves existing agent policy

The gateway SHALL assign public origin from the matched route and carry it with the turn. It SHALL wrap caller content with a gateway-authored instruction to follow the request only within existing policy and permissions. The caller's text, metadata, and reply directions SHALL be presented as quoted content.

#### Scenario: An admin uses a public route

- **WHEN** an admin credential holder chooses the public prompt route
- **THEN** the delivered prompt and its turn provenance identify public input

#### Scenario: Caller supplies an administrator claim in text

- **WHEN** public text includes instructions or markers claiming another origin or authority
- **THEN** the text remains inside the quoted content of the gateway-authored public envelope

### Requirement: Public input carries ordinary execution authority

Public input SHALL use readiness, pending-input, hook, incarnation, and finite-handoff guards. It SHALL use the current conversation without consuming admin session or model overrides. Its schema SHALL reject control fields. Native-looking command and raw-key text SHALL be inserted as literal content.

#### Scenario: Public caller submits a native command string

- **WHEN** public input includes text resembling a native control action
- **THEN** delivery uses the literal public envelope in the current conversation

#### Scenario: Public caller supplies control fields

- **WHEN** a public request supplies admission policy, session or model selection, interruption, or scheduling fields
- **THEN** validation rejects the request before dispatch

#### Scenario: Admin has prepared a one-shot session change

- **WHEN** a public input request arrives while an admin override is pending
- **THEN** its dispatch preserves that override for an eligible admin request

### Requirement: Public requests return only handoff outcomes

Public success SHALL confirm handoff to the captured body and return the source event ID. The HTTP contract SHALL be limited to handoff, refusal, and uncertainty. The gateway SHALL treat a caller's requested reply channel as content for the agent to evaluate under its existing policy.

#### Scenario: Public prompt requests an answer by mail

- **WHEN** public prompt text asks the agent to deliver a result to an email address or agreed shared file
- **THEN** the gateway renders that direction as content and instructs the agent to honor it only if policy permits
- **AND** the HTTP response contains only the handoff outcome, with any answer delivered separately by the agent

#### Scenario: Target is busy or unavailable

- **WHEN** a public request reaches a target that cannot admit ordinary work
- **THEN** it receives an immediate conflict or unavailable result
- **AND** a later ready state produces no delivery until the sender makes another request

#### Scenario: Confirmation or body identity is lost

- **WHEN** the gateway cannot confirm handoff to the captured body
- **THEN** it reports refusal or uncertainty and retains no request for later delivery
- **AND** a sender retry after uncertain handoff may duplicate delivery

### Requirement: Owner-file inputs on private mail routes follow current elevated access

Private send and reply forms with an owner-local attachment path SHALL require current anonymous open access or verified admin proof. A current self caller can use ordinary forms that omit these inputs. The gateway SHALL check path-form authority before filesystem or provider access. Admin-class post SHALL apply its own route admission and attachment validation.

#### Scenario: Self supplies an owner-local file path

- **WHEN** a self caller supplies an owner-local attachment path in send or reply while the roster has keys
- **THEN** the gateway returns HTTP 403 before opening the path or invoking a provider

#### Scenario: Self sends mail without owner-file inputs

- **WHEN** a self caller supplies a valid ordinary send or reply with no owner-local attachment paths
- **THEN** the operation uses the configured mailbox owner and its normal delivery semantics

#### Scenario: Admitted caller attaches an owner-local file

- **WHEN** an admitted caller uses an existing supported local-path attachment form
- **THEN** the path is interpreted in the recorded owner context under existing attachment validation

#### Scenario: An anonymous caller uses an owner-file attachment

- **WHEN** an unsigned caller uses a supported attachment form under a valid empty roster
- **THEN** the gateway rechecks the open grant before applying the existing attachment validation
- **AND THEN** delivery uses the configured mailbox binding and records anonymous caller provenance
