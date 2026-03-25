## Purpose
Define the public `houmao-mgr` contract as the Houmao-managed CAO-compatible service-management CLI and its paired relationship with `houmao-server`.
## Requirements
### Requirement: `houmao-mgr` reserves the top-level namespace for Houmao-owned pair commands
`houmao-mgr` SHALL reserve its top-level command namespace for Houmao-owned pair semantics.

CAO-compatible command entrypoints SHALL live only under the explicit `houmao-mgr cao ...` namespace.

Top-level CAO verbs such as `info`, `shutdown`, `init`, `flow`, `mcp-server`, and `install` SHALL NOT remain supported as top-level aliases.

Top-level `launch` MAY remain, but it SHALL be documented and implemented as a Houmao-owned pair command rather than as a top-level CAO compatibility verb.

#### Scenario: Removed top-level CAO verb is replaced by the explicit `cao` namespace
- **WHEN** an operator needs the CAO-compatible info command through `houmao-mgr`
- **THEN** the supported invocation is `houmao-mgr cao info`
- **AND THEN** `houmao-mgr` does not require top-level `info` compatibility to remain available

#### Scenario: Top-level pair launch workflow remains available after the boundary reset
- **WHEN** an operator wants the canonical pair launch workflow
- **THEN** the operator uses top-level `houmao-mgr launch`
- **AND THEN** that command is treated as Houmao-owned pair UX rather than a CAO compatibility alias

#### Scenario: Removed top-level install does not remain part of the pair workflow
- **WHEN** an operator tries to use top-level `houmao-mgr install`
- **THEN** that command is not part of the supported top-level `houmao-mgr` surface
- **AND THEN** migration guidance points the operator at native agent-definition-based launch instead of preinstalled compatibility profiles

### Requirement: `houmao-mgr` exposes a CAO-compatible command surface
The system SHALL expose a CAO-compatible command surface on a dedicated service-management binary named `houmao-mgr`.

For the supported `cao` version pinned by this capability, `houmao-mgr` SHALL accept the CAO-compatible command family under the explicit `houmao-mgr cao ...` namespace rather than as a drop-in top-level alias for `cao`.

At minimum, the CAO-compatible command family under `houmao-mgr cao` SHALL include:

- `flow`
- `info`
- `init`
- `launch`
- `mcp-server`
- `shutdown`

This capability SHALL NOT require aliasing `cao` directly to `houmao-mgr`, and it SHALL NOT require top-level `houmao-mgr` commands to preserve CAO command identity.

This capability SHALL NOT repurpose the existing `houmao-cli` binary as the CAO-compatible service-management surface.

#### Scenario: Explicit `cao` namespace accepts supported CAO-compatible command patterns
- **WHEN** an operator invokes a supported CAO-compatible command pattern through `houmao-mgr cao ...`
- **THEN** `houmao-mgr` accepts that command pattern with CAO-compatible behavior
- **AND THEN** the operator does not need top-level CAO verb compatibility to access the explicit compatibility surface

### Requirement: Session-backed compatibility commands use Houmao-owned pair authority
When a supported `houmao-mgr cao ...` command creates, inspects, mutates, or shuts down a session in the supported pair, `houmao-mgr` SHALL execute that behavior through Houmao-owned pair APIs rather than through an external `cao` subprocess.

This requirement applies at minimum to `houmao-mgr cao launch`, `houmao-mgr cao info`, and `houmao-mgr cao shutdown`.

#### Scenario: Namespaced compatibility launch uses the pair authority directly
- **WHEN** an operator runs `houmao-mgr cao launch ...` against the supported pair
- **THEN** `houmao-mgr` launches the session through Houmao-owned pair authority
- **AND THEN** it does not shell out to an external `cao` executable to complete the launch

#### Scenario: Namespaced compatibility info stays within the supported pair
- **WHEN** an operator runs `houmao-mgr cao info`
- **THEN** `houmao-mgr` reads compatibility-significant session information through Houmao-owned pair authority
- **AND THEN** the command does not require a raw `cao-server` deployment as its supported target

### Requirement: Session-backed pair launch resolves native agent definitions instead of installed compatibility profiles
For session-backed TUI launch in the supported pair, top-level `houmao-mgr launch` and explicit `houmao-mgr cao launch` SHALL interpret `--agents` as a native launch selector resolved from the effective agent-definition root rather than as a preinstalled compatibility profile name.

The effective agent-definition root used by session-backed launch SHALL follow the same native root contract used by top-level native headless translation.

In the first cut, session-backed selector resolution SHALL support tool-lane brain recipes from that root for the selected provider or tool lane.

This first cut SHALL NOT require blueprint-by-name resolution on the session-backed pair-launch surface.

Session-backed launch SHALL NOT require a separate public install step to preload compatibility profile state before launch.

When the resolved native launch target has no role binding or no matching role package, session-backed launch SHALL remain valid and SHALL treat that launch as a brain-only launch with an empty system prompt.

#### Scenario: Session-backed top-level launch resolves a native selector without install
- **WHEN** an operator runs `houmao-mgr launch --agents gpu-kernel-coder --provider codex`
- **THEN** `houmao-mgr` resolves `gpu-kernel-coder` from the effective native agent-definition root for that launch
- **AND THEN** the resolved native target comes from the selected tool lane's recipe store rather than a preinstalled compatibility profile
- **AND THEN** the launch does not require prior `houmao-mgr install` or any preloaded compatibility profile state

#### Scenario: Namespaced compatibility launch accepts a brain-only native target
- **WHEN** an operator runs `houmao-mgr cao launch ...` and the resolved native launch target has no role package
- **THEN** `houmao-mgr` still launches that session-backed agent through the supported pair
- **AND THEN** the launch uses an empty system prompt instead of failing for missing role metadata

### Requirement: `houmao-mgr` compatibility is pinned to one exact CAO source of truth
For this capability, the CAO CLI compatibility source of truth SHALL be pinned to:

- repository: `https://github.com/imsight-forks/cli-agent-orchestrator.git`
- commit: `0fb3e5196570586593736a21262996ca622f53b6`
- local tracked checkout: `extern/tracked/cli-agent-orchestrator`

The system SHALL treat that exact source as the parity oracle for `houmao-mgr` CLI compatibility rather than a floating branch name or whichever `cao` happens to be on `PATH`.

#### Scenario: CLI parity verification uses the pinned CAO source
- **WHEN** implementation or verification compares `houmao-mgr` behavior to CAO CLI behavior
- **THEN** it uses the pinned CAO source of truth for this capability
- **AND THEN** the parity target does not drift with a floating upstream branch

### Requirement: `houmao-mgr` compatibility is defined within the supported Houmao pair
The compatibility contract for `houmao-mgr` SHALL be defined as part of the supported `houmao-server + houmao-mgr` replacement pair for `cao-server + cao`.

This capability SHALL NOT require `houmao-mgr` to support arbitrary external `cao-server` deployments as a public compatibility contract.

Mixed-pair usage such as `cao-server + houmao-mgr` SHALL be treated as unsupported in this capability.

#### Scenario: Mixed raw-CAO-server-plus-`houmao-mgr` usage is not part of the compatibility promise
- **WHEN** an operator uses `houmao-mgr` against a raw `cao-server` deployment
- **THEN** that combination is outside the supported compatibility contract for this capability
- **AND THEN** parity verification for the capability does not need to claim that mixed pair works

### Requirement: Houmao extensions on `houmao-mgr` are additive only
When `houmao-mgr` extends an existing CAO-compatible command under the explicit `cao` namespace, those extensions SHALL be additive only.

Additive extensions MAY include:

- additional optional flags or arguments
- additional optional structured output fields where machine-readable output already exists
- additional new commands outside the supported CAO-compatible command family

`houmao-mgr` SHALL NOT require Houmao-only flags or arguments in order for a CAO-compatible invocation under `houmao-mgr cao ...` to succeed, and it SHALL NOT remove or repurpose CAO-defined command behavior for that explicit compatibility family.

This additive-only restriction SHALL apply to the `cao` namespace. It SHALL NOT require top-level Houmao-owned commands to preserve CAO flag shape, default behavior, or output wording.

#### Scenario: CAO-compatible invocation works under `cao` without Houmao-only flags
- **WHEN** an operator runs a supported CAO-compatible `houmao-mgr cao` command without any Houmao-only extension flags
- **THEN** `houmao-mgr` processes that invocation with CAO-compatible behavior
- **AND THEN** Houmao-only extensions remain optional rather than mandatory for compatibility

#### Scenario: Top-level Houmao-owned command may diverge from CAO wording or defaults
- **WHEN** an operator runs a top-level `houmao-mgr` command outside the `cao` namespace
- **THEN** that command may use Houmao-defined semantics, defaults, or output
- **AND THEN** the CAO additive-only rule remains scoped to `houmao-mgr cao ...`

### Requirement: Pair compatibility launch preserves the current provider surface explicitly
The supported pair SHALL preserve the current compatibility launch provider identifiers accepted by `houmao-mgr launch` and `houmao-mgr cao launch` in v1.

At minimum, that preserved provider surface SHALL include:

- `kiro_cli`
- `claude_code`
- `codex`
- `gemini_cli`
- `kimi_cli`
- `q_cli`

If a later change intentionally narrows or retires any of those provider identifiers, it SHALL do so explicitly rather than as an implicit side effect of removing CAO.

#### Scenario: Namespaced compatibility launch preserves a non-headless provider id
- **WHEN** an operator runs `houmao-mgr cao launch --provider q_cli ...` against the supported pair
- **THEN** `houmao-mgr` accepts that current compatibility provider identifier through Houmao-owned pair authority
- **AND THEN** the command does not require an external `cao` subprocess to preserve that launch surface

### Requirement: Session-backed `houmao-mgr cao` wrappers preserve compatibility-significant script-facing behavior
When `houmao-mgr` implements a session-backed CAO-compatible command under the explicit `cao` namespace as a repo-owned wrapper rather than blind passthrough, that wrapper SHALL preserve upstream-compatible exit-code behavior and compatibility-significant stdout or stderr behavior wherever upstream CAO already exposes machine-readable or script-consumed output.

This requirement SHALL apply at minimum to session-backed compatibility commands such as `houmao-mgr cao launch`, `houmao-mgr cao info`, and `houmao-mgr cao shutdown` when they are implemented over the supported pair boundary.

This requirement SHALL NOT force byte-for-byte parity for every human-oriented line of prose emitted by wrapper-owned messaging, as long as script-facing compatibility behavior remains intact.

#### Scenario: Wrapper preserves machine-readable or script-consumed compatibility output
- **WHEN** `houmao-mgr cao info` or another session-backed compatibility wrapper exposes upstream CAO output that scripts consume by exit code, JSON shape, or other machine-readable contract
- **THEN** the wrapper preserves that compatibility-significant behavior while operating through the supported pair boundary
- **AND THEN** pair-aware implementation details do not silently break script-facing CAO usage

#### Scenario: Human-oriented prose may differ without breaking the compatibility contract
- **WHEN** a session-backed `houmao-mgr cao` wrapper emits additional or reworded human-oriented status text that is not part of a machine-readable CAO contract
- **THEN** the command may still satisfy the explicit compatibility namespace contract
- **AND THEN** the wrapper continues preserving upstream-compatible exit codes and script-facing output behavior

### Requirement: Most CAO-compatible CLI work uses Houmao-owned compatibility implementations
The supported `houmao-mgr cao ...` command family SHALL be implemented by Houmao-owned compatibility code rather than by delegating to an installed `cao` executable.

For session-backed compatibility commands, `houmao-mgr` SHALL use pair-aware implementations over the supported `houmao-server` boundary.

For local-only compatibility commands that remain part of the documented command family, `houmao-mgr` SHALL use Houmao-owned compatibility helpers rather than shelling out to external `cao`.

The supported pair SHALL NOT require `cao` to be installed on `PATH` in order for the documented `houmao-mgr cao ...` surface to work.

#### Scenario: Local-only compatibility command works without installed `cao`
- **WHEN** an operator invokes a documented local-only compatibility command such as `houmao-mgr cao flow list`
- **THEN** `houmao-mgr` satisfies that command through Houmao-owned compatibility code
- **AND THEN** the operator does not need `cao` installed on `PATH`

#### Scenario: Server-backed compatibility command uses a pair-aware wrapper
- **WHEN** an operator invokes a server-backed compatibility command such as `houmao-mgr cao info`
- **THEN** `houmao-mgr` satisfies that CAO-compatible UX through a repo-owned pair-aware implementation
- **AND THEN** the command does not depend on blind subprocess passthrough to remain part of the supported compatibility surface

### Requirement: Agent-creating CLI flows register live agents with `houmao-server`
When a session-backed `houmao-mgr` launch flow creates or launches a live agent session inside the supported Houmao pair, `houmao-mgr` SHALL register the resulting live agent with `houmao-server`.

For v1, successful top-level `houmao-mgr launch ...` TUI launches and successful `houmao-mgr cao launch ...` compatibility launches SHALL satisfy this registration contract when they target the supported pair.

That registration SHALL supplement the underlying session creation behavior rather than replacing it in the shallow cut.

#### Scenario: Top-level pair launch registers the live agent with `houmao-server`
- **WHEN** an operator runs a successful top-level `houmao-mgr launch ...` for a TUI-backed session
- **THEN** `houmao-mgr` registers the resulting live agent or session with `houmao-server`
- **AND THEN** `houmao-server` can begin managing watch or state features for that launched agent

#### Scenario: Namespaced compatibility launch also registers with `houmao-server`
- **WHEN** an operator runs a successful `houmao-mgr cao launch ...` against the supported pair
- **THEN** `houmao-mgr` registers the resulting live agent or session with `houmao-server`
- **AND THEN** the explicit compatibility namespace does not create an untracked pair session

### Requirement: Successful delegated launches materialize Houmao-owned authoritative session artifacts
When a session-backed `houmao-mgr` launch succeeds through delegated or compatibility-preserving behavior inside the supported Houmao pair, it SHALL materialize Houmao-owned authoritative session artifacts for that launched session rather than leaving the launch server-only.

At minimum, that materialization SHALL:

- create or update a Houmao runtime-owned session root
- write a runtime-owned manifest that uses `backend = "houmao_server_rest"`
- let any transitional shared-registry publication point back to that manifest and session root
- keep later gateway and mailbox follow-up flows able to reuse those manifest-backed artifacts while those subsystems still depend on runtime-owned manifests

#### Scenario: Session-backed launch writes a Houmao-owned manifest for later reuse
- **WHEN** an operator runs a successful session-backed `houmao-mgr` launch flow inside the supported pair
- **THEN** `houmao-mgr` materializes a Houmao-owned session root and manifest for that launched session
- **AND THEN** later discovery, gateway, or mailbox follow-up flows can point back to those artifacts instead of depending on a separate server-only truth

### Requirement: `houmao-mgr launch --headless` targets `houmao-server` native headless launch
When an operator invokes top-level `houmao-mgr launch` with the additive `--headless` flag against a supported Houmao pair, `houmao-mgr` SHALL treat that invocation as a Houmao-owned native headless launch path rather than delegating that headless case to CAO compatibility behavior.

That native headless launch path SHALL target a Houmao-owned `houmao-server` endpoint for headless launch and SHALL use the server-returned managed-agent identity and runtime pointers for any follow-up reporting or artifact materialization required by the pair.

For the headless case, top-level `houmao-mgr launch` SHALL translate pair convenience inputs such as `--agents`, `--provider`, and the current working directory into the resolved native launch request expected by `houmao-server`.

That translation SHALL produce the resolved runtime launch inputs required by the raw server contract, such as `tool`, `working_directory`, `agent_def_dir`, `brain_manifest_path`, and `role_name`, or SHALL fail explicitly before launch if it cannot resolve them.

The explicit compatibility command `houmao-mgr cao launch` SHALL remain a CAO-compatible launch surface and SHALL NOT redefine top-level `launch --headless` as a CAO compatibility contract.

#### Scenario: Top-level headless launch does not delegate to CAO compatibility
- **WHEN** an operator runs `houmao-mgr launch --headless --agents gpu-kernel-coder --provider claude_code`
- **THEN** `houmao-mgr` routes that request to `houmao-server` native headless launch
- **AND THEN** it does not require a CAO-compatible launch path to create a CAO session or terminal for that headless agent

#### Scenario: Namespaced compatibility launch remains distinct from top-level native headless launch
- **WHEN** an operator uses `houmao-mgr cao launch ...`
- **THEN** that command remains part of the explicit CAO compatibility namespace
- **AND THEN** it does not redefine the top-level `launch --headless` contract as a CAO compatibility feature

### Requirement: `houmao-mgr` compatibility SHALL be verified against a real `cao` CLI
The implementation SHALL include verification that compares the explicit `houmao-mgr cao ...` command surface to the pinned CAO source and exercises the compatibility commands through the Houmao-owned implementations that replace external `cao` delegation.

Where a real CAO CLI invocation remains the most direct parity oracle, verification MAY use it as an oracle. The supported product path SHALL NOT depend on that CLI being present.

That compatibility verification SHALL cover at minimum:

- command availability under the `cao` namespace
- argument parsing for the CAO-compatible command family
- script-facing exit-code and machine-readable output behavior
- pair-aware wrapper behavior where explicit pair routing replaces blind passthrough
- local compatibility-helper behavior for namespaced commands that remain local-only
- supported-pair enforcement where Houmao intentionally rejects mixed-pair usage

Houmao-owned CLI behavior SHALL be tested directly and more strictly. That verification SHALL cover at minimum:

- native headless top-level `launch --headless`
- session-backed top-level `launch` registration and runtime artifact materialization
- namespaced compatibility launch/info/shutdown through the pair
- native selector resolution for both headless and session-backed launch, including brain-only empty-prompt behavior

#### Scenario: Compatibility verification catches namespace regressions
- **WHEN** a `houmao-mgr cao` command changes in a way that breaks CAO-compatible invocation shape or compatibility-significant behavior
- **THEN** compatibility verification detects the divergence
- **AND THEN** the implementation can reject that change before claiming namespaced CAO compatibility

#### Scenario: Houmao-owned verification catches pair-command regressions
- **WHEN** a top-level or namespaced Houmao-owned command changes in a way that breaks pair launch, native selector resolution, or compatibility-wrapper behavior
- **THEN** direct Houmao behavior verification detects the regression
- **AND THEN** the implementation can reject that change even though no external `cao` subprocess is involved

### Requirement: Delegated launch preserves authoritative tmux window identity
When `houmao-mgr launch` completes successfully inside the supported pair, it SHALL recover tmux window identity from the pair authority's session-detail response and SHALL persist that window identity into Houmao-owned registration and runtime artifacts whenever the metadata is available.

This preservation SHALL use the authoritative session-detail response rather than deriving tmux window identity from `terminal_id` or another unrelated field.

#### Scenario: Launch registration preserves tmux window identity from session detail
- **WHEN** `houmao-mgr launch` receives a successful session-detail response whose terminal summary includes tmux window metadata
- **THEN** `houmao-mgr` includes that tmux window identity in the registration payload sent to `houmao-server`
- **AND THEN** the corresponding Houmao-owned runtime artifacts persist the same window identity for later tracking and resume flows

#### Scenario: Missing tmux window metadata does not fabricate a value
- **WHEN** a successful delegated launch does not expose tmux window metadata in the session-detail response
- **THEN** `houmao-mgr` leaves that field unset in its Houmao-owned follow-up artifacts
- **AND THEN** the CLI does not invent a replacement value from `terminal_id` or another incompatible field

### Requirement: Session-backed compatibility launch exposes additive timeout override controls
Session-backed pair launch SHALL expose additive operator controls for the CAO-compatible client timeout budgets used during compatibility launch.

At minimum, the session-backed launch surfaces SHALL accept:

- `--compat-http-timeout-seconds`
- `--compat-create-timeout-seconds`

When those flags are omitted, the session-backed launch surfaces SHALL resolve defaults from these optional environment variables before falling back to built-in client defaults:

- `HOUMAO_COMPAT_HTTP_TIMEOUT_SECONDS`
- `HOUMAO_COMPAT_CREATE_TIMEOUT_SECONDS`

CLI flags SHALL take precedence over environment-variable defaults.

This requirement SHALL apply to:

- `houmao-mgr cao launch`
- top-level `houmao-mgr launch` when it is using the session-backed TUI compatibility path

These additive timeout controls SHALL affect only the CAO-compatible pair client used for session-backed launch. They SHALL NOT redefine the native headless launch contract.

#### Scenario: Namespaced compatibility launch accepts additive timeout overrides
- **WHEN** an operator runs `houmao-mgr cao launch --compat-create-timeout-seconds 90 ...`
- **THEN** `houmao-mgr` uses a 90-second create-operation timeout budget for the compatibility session-creation request
- **AND THEN** the command remains valid without requiring any Houmao-only timeout flag for ordinary compatibility usage

#### Scenario: Environment default applies when explicit timeout flags are omitted
- **WHEN** an operator sets `HOUMAO_COMPAT_HTTP_TIMEOUT_SECONDS` and `HOUMAO_COMPAT_CREATE_TIMEOUT_SECONDS`
- **AND WHEN** the operator runs a session-backed compatibility launch without the corresponding flags
- **THEN** `houmao-mgr` uses those environment-provided timeout budgets for the compatibility client
- **AND THEN** an explicit flag would override the environment value if later provided

#### Scenario: Native headless launch rejects compatibility-only timeout flags
- **WHEN** an operator runs top-level `houmao-mgr launch --headless` and also supplies `--compat-http-timeout-seconds` or `--compat-create-timeout-seconds`
- **THEN** the command fails explicitly
- **AND THEN** it does not imply that native headless launch honors CAO-compatible timeout controls
