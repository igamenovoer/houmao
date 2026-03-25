## REMOVED Requirements

### Requirement: `houmao-mgr` exposes a CAO-compatible command surface
**Reason**: The CAO compatibility layer is no longer needed. Agent launch moves to `houmao-mgr agents launch` (local, server-independent). Server session management moves to `houmao-mgr server sessions`. The `cao` namespace added confusion without unique functionality.
**Migration**: Use `houmao-mgr agents launch` instead of `houmao-mgr cao launch`. Use `houmao-mgr server sessions shutdown` instead of `houmao-mgr cao shutdown`. Use `houmao-mgr server status` instead of `houmao-mgr cao info`.

### Requirement: Session-backed compatibility commands use Houmao-owned pair authority
**Reason**: Retired along with the `cao` namespace. Session-backed launch through the server is replaced by direct local launch via `houmao-mgr agents launch`.
**Migration**: Use `houmao-mgr agents launch` for agent launch. Server-backed session management available via `houmao-mgr server sessions`.

### Requirement: Session-backed pair launch resolves native agent definitions instead of installed compatibility profiles
**Reason**: The native selector resolution behavior is preserved in `houmao-mgr agents launch`. The requirement was scoped to the `cao launch` and top-level `launch` paths which are retired.
**Migration**: `houmao-mgr agents launch --agents <selector>` uses the same `resolve_native_launch_target()` resolution.

### Requirement: `houmao-mgr` compatibility is pinned to one exact CAO source of truth
**Reason**: No longer maintaining CAO CLI compatibility. The `cao` namespace is retired.
**Migration**: No replacement needed. The pinned CAO source remains in `extern/tracked/` for reference but is not used for compatibility verification.

### Requirement: `houmao-mgr` compatibility is defined within the supported Houmao pair
**Reason**: Retired along with the CAO compatibility concept. The supported pair relationship remains for server-backed features but is no longer framed as CAO compatibility.
**Migration**: No direct replacement. Server interaction is now explicit via `houmao-mgr server *`.

### Requirement: Houmao extensions on `houmao-mgr` are additive only
**Reason**: The additive-only constraint was scoped to preserving CAO command compatibility under the `cao` namespace. With the namespace retired, this constraint is no longer applicable.
**Migration**: No replacement needed. Houmao-owned commands evolve freely.

### Requirement: Pair compatibility launch preserves the current provider surface explicitly
**Reason**: Provider identifiers are preserved in `houmao-mgr agents launch`. The requirement was scoped to the `cao launch` compatibility surface.
**Migration**: `houmao-mgr agents launch --provider <id>` accepts the same provider identifiers.

### Requirement: Session-backed `houmao-mgr cao` wrappers preserve compatibility-significant script-facing behavior
**Reason**: Retired along with the `cao` namespace wrappers.
**Migration**: No replacement. Scripts should migrate to `houmao-mgr agents launch` and `houmao-mgr server *`.

### Requirement: Most CAO-compatible CLI work uses Houmao-owned compatibility implementations
**Reason**: Retired along with the `cao` namespace. The requirement ensured CAO commands used Houmao code rather than shelling out to `cao`. With no `cao` commands, this is moot.
**Migration**: No replacement needed.

### Requirement: Agent-creating CLI flows register live agents with `houmao-server`
**Reason**: Agent registration now goes to the shared registry via `publish_live_agent_record()`, not to `houmao-server`. The server is no longer in the agent launch path.
**Migration**: `houmao-mgr agents launch` publishes to the shared registry. Server-side tracking is optional and happens via the `houmao-mgr server` surface.

### Requirement: Successful delegated launches materialize Houmao-owned authoritative session artifacts
**Reason**: Delegated launch (where the server builds the brain and the client creates stub artifacts) is replaced by direct local launch. No stub manifests are needed when the client does real brain building.
**Migration**: `houmao-mgr agents launch` creates real brain manifests and session artifacts directly via `start_runtime_session()`.

### Requirement: `houmao-mgr launch --headless` targets `houmao-server` native headless launch
**Reason**: Top-level `launch` is retired. Headless launch is available via `houmao-mgr agents launch --headless` and does not route through the server.
**Migration**: Use `houmao-mgr agents launch --headless --agents <selector> --provider <provider>`.

### Requirement: `houmao-mgr` compatibility SHALL be verified against a real `cao` CLI
**Reason**: No longer maintaining CAO CLI compatibility. Verification is against Houmao-owned specs, not the CAO CLI.
**Migration**: Tests verify `houmao-mgr agents launch`, `houmao-mgr server *`, and `houmao-mgr agents *` directly.

### Requirement: Delegated launch preserves authoritative tmux window identity
**Reason**: Delegated launch (where the server creates the tmux session and the client registers post-hoc) is retired. With local launch, `start_runtime_session()` creates the tmux session directly and owns the window identity from the start.
**Migration**: `houmao-mgr agents launch` via `start_runtime_session()` creates and owns tmux session/window identity natively.

### Requirement: Session-backed compatibility launch exposes additive timeout override controls
**Reason**: The `--compat-http-timeout-seconds` and `--compat-create-timeout-seconds` flags were for the CAO-compatible client timeout budget during server-mediated launch. With local launch, there is no server HTTP call in the launch path.
**Migration**: No replacement needed. Server communication timeouts for post-launch operations are handled by the existing client infrastructure.

### Requirement: `houmao-mgr` reserves the top-level namespace for Houmao-owned pair commands
**Reason**: The constraint was about keeping CAO verbs out of the top-level namespace while preserving them under `cao`. With `cao` retired entirely, this namespace governance rule is superseded by the simpler structure: `server`, `agents`, `brains`, `admin` at top level.
**Migration**: Governed by the modified `houmao-srv-ctrl-native-cli` spec which defines the new top-level command tree.
