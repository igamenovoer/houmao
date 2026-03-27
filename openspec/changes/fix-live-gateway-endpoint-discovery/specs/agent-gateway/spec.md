## MODIFIED Requirements

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
