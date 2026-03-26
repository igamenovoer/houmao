## MODIFIED Requirements

### Requirement: Pair-owned gateway attach for managed `houmao_server_rest` sessions supports explicit and current-session targeting
The system SHALL expose `houmao-mgr agents gateway attach` as the pair-owned gateway attach surface for pair-managed tmux-backed TUI sessions whose runtime backend is `houmao_server_rest`.

When called with an explicit managed-agent selector, the command SHALL resolve the target through the Houmao managed-agent identity namespace and SHALL execute attach through the managed-agent gateway attach route rather than through raw `cao` or raw runtime CLI semantics.

When called through the current-session contract, the command SHALL require execution inside the target agent's tmux session, SHALL discover the current tmux session as the attach context, SHALL prefer `AGENTSYS_MANIFEST_PATH` from that tmux session when present and valid, SHALL otherwise use `AGENTSYS_AGENT_ID` from that same tmux session to resolve exactly one fresh shared-registry record and `runtime.manifest_path`, SHALL require the resolved manifest to belong to the current tmux session, SHALL derive attach authority from that manifest, and SHALL refuse the attach when those inputs are missing, stale, ambiguous, identify a non-`houmao_server_rest` session, or fail to resolve exactly one managed agent on the persisted pair authority.

`houmao-mgr` SHALL NOT require the user to address raw `cao_rest` or child-CAO topology in order to attach a gateway for pair-managed sessions, and current-session attach SHALL NOT fall back to `AGENTSYS_GATEWAY_ATTACH_PATH`, `AGENTSYS_GATEWAY_ROOT`, `terminal_id`, cwd, ambient shell env, or another server target when manifest or shared-registry discovery is invalid or stale.

#### Scenario: Explicit attach resolves through managed-agent identity
- **WHEN** a developer runs `houmao-mgr agents gateway attach --agent-id abc123` for a pair-managed `houmao_server_rest` session
- **THEN** the command resolves that target through the managed-agent identity namespace
- **AND THEN** the attach request is issued through the Houmao managed-agent gateway lifecycle surface

#### Scenario: Current-session attach prefers the tmux-published manifest pointer
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from inside a pair-managed agent tmux session
- **AND WHEN** that tmux session publishes a valid `AGENTSYS_MANIFEST_PATH`
- **THEN** the command loads that manifest directly as the current-session attach authority
- **AND THEN** the command does not require an explicit agent identity

#### Scenario: Current-session attach falls back to shared registry by agent id
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from inside a pair-managed agent tmux session
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` is missing, blank, or stale in that session
- **AND WHEN** the tmux session publishes `AGENTSYS_AGENT_ID`
- **THEN** the command resolves exactly one fresh shared-registry record by that authoritative `agent_id`
- **AND THEN** it uses the resolved `runtime.manifest_path` as the attach authority input

#### Scenario: Current-session attach uses manifest-declared server authority
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from inside a pair-managed agent tmux session
- **AND WHEN** the resolved manifest declares attach authority `api_base_url=<server>` with managed-agent ref `<agent-ref>`
- **THEN** the command issues the managed-agent gateway attach request against `<server>` with `<agent-ref>` as `{agent_ref}`
- **AND THEN** it does not retarget the request through legacy gateway pointers, `terminal_id`, or another alias

#### Scenario: Current-session attach fails closed without usable manifest-first discovery
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from a tmux session whose `AGENTSYS_MANIFEST_PATH` is unusable
- **AND WHEN** `AGENTSYS_AGENT_ID` is missing, stale, or does not resolve exactly one fresh shared-registry record
- **THEN** the command fails explicitly
- **AND THEN** it does not guess from cwd, ambient shell env, or raw CAO state

### Requirement: Stable attachability metadata is distinct from live gateway bindings
The system SHALL publish stable attachability metadata for gateway-capable sessions independently from whether a gateway process is currently running.

Stable attachability metadata SHALL be sufficient for a later attach flow to determine how to attach to the live session through `manifest.json` together with tmux-local discovery and shared-registry fallback. `gateway_manifest.json` MAY exist as derived outward-facing gateway bookkeeping, but SHALL NOT be the authoritative input for attach resolution.

Live gateway bindings such as active host, port, and state-path pointers SHALL describe only the currently running gateway instance and SHALL be treated as ephemeral.

#### Scenario: Gateway-capable session exists with no running gateway
- **WHEN** a tmux-backed session has published manifest-backed attach metadata but no gateway companion is currently running
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

## ADDED Requirements

### Requirement: Native headless gateway attach supports tmux current-session targeting without requiring a live worker process
For native headless tmux-backed sessions, the system SHALL allow gateway attach from inside the owning tmux session using manifest-first discovery from `AGENTSYS_MANIFEST_PATH` or `AGENTSYS_AGENT_ID`.

Current-session headless attach SHALL target the logical headless session described by the manifest rather than assuming a currently running headless worker process already exists.

The system SHALL keep tmux window `0` reserved for the headless agent console surface, and any same-session gateway surface used during attach SHALL remain off window `0`.

When the resolved manifest declares native headless relaunch authority, gateway attach SHALL treat that manifest-owned authority as sufficient to manage future headless turns even when no current headless process pid is published.

#### Scenario: Current-session headless attach uses manifest-first discovery
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from inside a native headless tmux session
- **AND WHEN** that session publishes a valid `AGENTSYS_MANIFEST_PATH`
- **THEN** the command loads that manifest as the current-session attach authority
- **AND THEN** it does not require a currently running headless worker process

#### Scenario: Headless attach falls back to shared registry by agent id
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from inside a native headless tmux session
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` is missing, blank, or stale
- **AND WHEN** the tmux session publishes `AGENTSYS_AGENT_ID`
- **THEN** the command resolves exactly one fresh shared-registry record by that authoritative `agent_id`
- **AND THEN** it uses the resolved `runtime.manifest_path` as the attach authority input

#### Scenario: Headless attach succeeds between turns with no live agent pid
- **WHEN** a native headless session has a valid manifest and tmux discovery metadata
- **AND WHEN** no current headless worker process is running because the previous turn already ended
- **THEN** gateway attach remains valid for that logical session
- **AND THEN** the gateway uses manifest-owned launch authority to manage future turns

### Requirement: Gateway bootstrap artifacts are internal runtime state rather than supported public authority
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
