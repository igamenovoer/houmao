## ADDED Requirements

### Requirement: `houmao-srv-ctrl` reserves the top-level namespace for Houmao-owned pair commands
`houmao-srv-ctrl` SHALL reserve its top-level command namespace for Houmao-owned pair semantics.

CAO-compatible command entrypoints SHALL live only under the explicit `houmao-srv-ctrl cao ...` namespace.

Top-level CAO verbs such as `info`, `shutdown`, `init`, `flow`, and `mcp-server` SHALL NOT remain supported as top-level aliases.

Top-level `launch` and `install` MAY remain, but they SHALL be documented and implemented as Houmao-owned pair commands rather than top-level CAO compatibility verbs.

#### Scenario: Removed top-level CAO verb is replaced by the explicit `cao` namespace
- **WHEN** an operator needs the CAO-compatible info command through `houmao-srv-ctrl`
- **THEN** the supported invocation is `houmao-srv-ctrl cao info`
- **AND THEN** `houmao-srv-ctrl` does not require top-level `info` compatibility to remain available

#### Scenario: Top-level pair workflows remain available after the boundary reset
- **WHEN** an operator wants the canonical pair launch or install workflow
- **THEN** the operator uses top-level `houmao-srv-ctrl launch` or `houmao-srv-ctrl install`
- **AND THEN** those commands are treated as Houmao-owned pair UX rather than CAO compatibility aliases

## MODIFIED Requirements

### Requirement: `houmao-srv-ctrl` exposes a CAO-compatible command surface
The system SHALL expose a CAO-compatible command surface on a dedicated service-management binary named `houmao-srv-ctrl`.

For the supported `cao` version pinned by this capability, `houmao-srv-ctrl` SHALL accept the CAO-compatible command family under the explicit `houmao-srv-ctrl cao ...` namespace rather than as a drop-in top-level alias for `cao`.

At minimum, the CAO-compatible command family under `houmao-srv-ctrl cao` SHALL include:

- `flow`
- `info`
- `init`
- `install`
- `launch`
- `mcp-server`
- `shutdown`

This capability SHALL NOT require aliasing `cao` directly to `houmao-srv-ctrl`, and it SHALL NOT require top-level `houmao-srv-ctrl` commands to preserve CAO command identity.

This capability SHALL NOT repurpose the existing `houmao-cli` binary as the CAO-compatible service-management surface.

#### Scenario: Explicit `cao` namespace accepts supported CAO command patterns
- **WHEN** an operator invokes a supported CAO-compatible command pattern through `houmao-srv-ctrl cao ...`
- **THEN** `houmao-srv-ctrl` accepts that command pattern with CAO-compatible behavior
- **AND THEN** the operator does not need top-level CAO verb compatibility to access the explicit compatibility surface

### Requirement: Houmao extensions on `houmao-srv-ctrl` are additive only
When `houmao-srv-ctrl` extends an existing CAO-compatible command under the explicit `cao` namespace, those extensions SHALL be additive only.

Additive extensions MAY include:

- additional optional flags or arguments
- additional optional structured output fields where machine-readable output already exists
- additional new commands outside the supported CAO-compatible command family

`houmao-srv-ctrl` SHALL NOT require Houmao-only flags or arguments in order for a CAO-compatible invocation under `houmao-srv-ctrl cao ...` to succeed, and it SHALL NOT remove or repurpose CAO-defined command behavior for that explicit compatibility family.

This additive-only restriction SHALL apply to the `cao` namespace. It SHALL NOT require top-level Houmao-owned commands to preserve CAO flag shape, default behavior, or output wording.

#### Scenario: CAO-compatible invocation works under `cao` without Houmao-only flags
- **WHEN** an operator runs a supported CAO-compatible `houmao-srv-ctrl cao` command without any Houmao-only extension flags
- **THEN** `houmao-srv-ctrl` processes that invocation with CAO-compatible behavior
- **AND THEN** Houmao-only extensions remain optional rather than mandatory for compatibility

#### Scenario: Top-level Houmao-owned command may diverge from CAO wording or defaults
- **WHEN** an operator runs a top-level `houmao-srv-ctrl` command outside the `cao` namespace
- **THEN** that command may use Houmao-defined semantics, defaults, or output
- **AND THEN** the CAO additive-only rule remains scoped to `houmao-srv-ctrl cao ...`

### Requirement: Session-backed `houmao-srv-ctrl cao` wrappers preserve compatibility-significant script-facing behavior
When `houmao-srv-ctrl` implements a session-backed CAO-compatible command under the explicit `cao` namespace as a repo-owned wrapper rather than blind passthrough, that wrapper SHALL preserve upstream-compatible exit-code behavior and compatibility-significant stdout or stderr behavior wherever upstream CAO already exposes machine-readable or script-consumed output.

This requirement SHALL apply at minimum to session-backed compatibility commands such as `houmao-srv-ctrl cao launch`, `houmao-srv-ctrl cao info`, and `houmao-srv-ctrl cao shutdown` when they are implemented over the supported pair boundary.

This requirement SHALL NOT force byte-for-byte parity for every human-oriented line of prose emitted by wrapper-owned messaging, as long as script-facing compatibility behavior remains intact.

#### Scenario: Wrapper preserves machine-readable or script-consumed compatibility output
- **WHEN** `houmao-srv-ctrl cao info` or another session-backed compatibility wrapper exposes upstream CAO output that scripts consume by exit code, JSON shape, or other machine-readable contract
- **THEN** the wrapper preserves that compatibility-significant behavior while operating through the supported pair boundary
- **AND THEN** pair-aware implementation details do not silently break script-facing CAO usage

#### Scenario: Human-oriented prose may differ without breaking the compatibility contract
- **WHEN** a session-backed `houmao-srv-ctrl cao` wrapper emits additional or reworded human-oriented status text that is not part of a machine-readable CAO contract
- **THEN** the command may still satisfy the explicit compatibility namespace contract
- **AND THEN** the wrapper continues preserving upstream-compatible exit codes and script-facing output behavior

### Requirement: Most CAO-compatible CLI work delegates to the installed `cao` executable
For CAO-compatible commands that do not depend on pair-owned public server routing or Houmao-owned post-command side effects, `houmao-srv-ctrl` SHALL be allowed to call the installed `cao` executable internally rather than re-implementing CAO CLI behavior natively.

For CAO-compatible commands that do depend on the explicit pair boundary or Houmao-owned follow-up behavior, `houmao-srv-ctrl` SHALL be allowed to use repo-owned compatibility wrappers instead of blind subprocess passthrough.

At minimum, local-only compatibility commands such as `houmao-srv-ctrl cao init`, `houmao-srv-ctrl cao flow`, and `houmao-srv-ctrl cao mcp-server` MAY remain delegated to the installed `cao` executable.

At minimum, server-backed compatibility commands such as `houmao-srv-ctrl cao launch`, `houmao-srv-ctrl cao info`, and `houmao-srv-ctrl cao shutdown` MAY use pair-aware implementations over the supported `houmao-server` boundary instead of blind passthrough.

#### Scenario: Local-only compatibility command may delegate to installed `cao`
- **WHEN** an operator invokes a local-only compatibility command such as `houmao-srv-ctrl cao flow list`
- **THEN** `houmao-srv-ctrl` may delegate that command to the installed `cao` executable internally
- **AND THEN** the operator receives the compatibility result through `houmao-srv-ctrl`

#### Scenario: Server-backed compatibility command may use a pair-aware wrapper
- **WHEN** an operator invokes a server-backed compatibility command such as `houmao-srv-ctrl cao info`
- **THEN** `houmao-srv-ctrl` may satisfy that CAO-compatible UX through a repo-owned pair-aware implementation
- **AND THEN** the command does not need blind subprocess passthrough to remain part of the supported compatibility surface

### Requirement: Agent-creating CLI flows register live agents with `houmao-server`
When a session-backed `houmao-srv-ctrl` launch flow creates or launches a live agent session inside the supported Houmao pair, `houmao-srv-ctrl` SHALL register the resulting live agent with `houmao-server`.

For v1, successful top-level `houmao-srv-ctrl launch ...` TUI launches and successful `houmao-srv-ctrl cao launch ...` compatibility launches SHALL satisfy this registration contract when they target the supported pair.

That registration SHALL supplement the underlying session creation behavior rather than replacing it in the shallow cut.

#### Scenario: Top-level pair launch registers the live agent with `houmao-server`
- **WHEN** an operator runs a successful top-level `houmao-srv-ctrl launch ...` for a TUI-backed session
- **THEN** `houmao-srv-ctrl` registers the resulting live agent or session with `houmao-server`
- **AND THEN** `houmao-server` can begin managing watch or state features for that launched agent

#### Scenario: Namespaced compatibility launch also registers with `houmao-server`
- **WHEN** an operator runs a successful `houmao-srv-ctrl cao launch ...` against the supported pair
- **THEN** `houmao-srv-ctrl` registers the resulting live agent or session with `houmao-server`
- **AND THEN** the explicit compatibility namespace does not create an untracked pair session

### Requirement: Successful delegated launches materialize Houmao-owned authoritative session artifacts
When a session-backed `houmao-srv-ctrl` launch succeeds through delegated or compatibility-preserving behavior inside the supported Houmao pair, it SHALL materialize Houmao-owned authoritative session artifacts for that launched session rather than leaving the launch server-only.

At minimum, that materialization SHALL:

- create or update a Houmao runtime-owned session root
- write a runtime-owned manifest that uses `backend = "houmao_server_rest"`
- let any transitional shared-registry publication point back to that manifest and session root
- keep later gateway and mailbox follow-up flows able to reuse those manifest-backed artifacts while those subsystems still depend on runtime-owned manifests

#### Scenario: Session-backed launch writes a Houmao-owned manifest for later reuse
- **WHEN** an operator runs a successful session-backed `houmao-srv-ctrl` launch flow inside the supported pair
- **THEN** `houmao-srv-ctrl` materializes a Houmao-owned session root and manifest for that launched session
- **AND THEN** later discovery, gateway, or mailbox follow-up flows can point back to those artifacts instead of depending on a separate server-only truth

### Requirement: `houmao-srv-ctrl launch --headless` targets `houmao-server` native headless launch
When an operator invokes top-level `houmao-srv-ctrl launch` with the additive `--headless` flag against a supported Houmao pair, `houmao-srv-ctrl` SHALL treat that invocation as a Houmao-owned native headless launch path rather than delegating that headless case to CAO compatibility behavior.

That native headless launch path SHALL target a Houmao-owned `houmao-server` endpoint for headless launch and SHALL use the server-returned managed-agent identity and runtime pointers for any follow-up reporting or artifact materialization required by the pair.

For the headless case, top-level `houmao-srv-ctrl launch` SHALL translate pair convenience inputs such as `--agents`, `--provider`, and the current working directory into the resolved native launch request expected by `houmao-server`.

That translation SHALL produce the resolved runtime launch inputs required by the raw server contract, such as `tool`, `working_directory`, `agent_def_dir`, `brain_manifest_path`, and `role_name`, or SHALL fail explicitly before launch if it cannot resolve them.

The explicit compatibility command `houmao-srv-ctrl cao launch` SHALL remain a CAO-compatible launch surface and SHALL NOT redefine top-level `launch --headless` as a CAO compatibility contract.

#### Scenario: Top-level headless launch does not delegate to CAO compatibility
- **WHEN** an operator runs `houmao-srv-ctrl launch --headless --agents gpu-kernel-coder --provider claude_code`
- **THEN** `houmao-srv-ctrl` routes that request to `houmao-server` native headless launch
- **AND THEN** it does not require a CAO-compatible launch path to create a CAO session or terminal for that headless agent

#### Scenario: Namespaced compatibility launch remains distinct from top-level native headless launch
- **WHEN** an operator uses `houmao-srv-ctrl cao launch ...`
- **THEN** that command remains part of the explicit CAO compatibility namespace
- **AND THEN** it does not redefine the top-level `launch --headless` contract as a CAO compatibility feature

### Requirement: `houmao-srv-ctrl` compatibility SHALL be verified against a real `cao` CLI
The implementation SHALL include verification that compares the explicit `houmao-srv-ctrl cao ...` command surface to the pinned `cao` source and exercises the commands that remain delegated through real `cao` execution where delegation is still part of the design.

For compatibility commands implemented as repo-owned pair-aware wrappers, verification SHALL focus on whether `houmao-srv-ctrl` preserves the CAO-compatible command shape and compatibility-significant behavior while operating through the supported pair boundary.

That compatibility verification SHALL cover at minimum:

- command availability under the `cao` namespace
- argument parsing for the CAO-compatible command family
- real `cao` delegation where delegation remains part of the design
- pair-aware wrapper behavior where explicit pair routing replaces blind passthrough
- supported-pair enforcement where Houmao intentionally rejects mixed-pair usage

Houmao-owned top-level behavior SHALL be tested directly and more strictly. That verification SHALL cover at minimum:

- native headless top-level `launch --headless`
- session-backed top-level `launch` registration and runtime artifact materialization
- top-level `install` routing through `houmao-server`

#### Scenario: Compatibility verification catches `cao` namespace regressions
- **WHEN** a `houmao-srv-ctrl cao` command changes in a way that breaks CAO-compatible invocation shape or compatibility-significant behavior
- **THEN** compatibility verification detects the divergence
- **AND THEN** the implementation can reject that change before claiming namespaced CAO compatibility

#### Scenario: Houmao-owned top-level verification catches pair-command regressions
- **WHEN** a top-level Houmao-owned command changes in a way that breaks pair launch or install behavior
- **THEN** direct Houmao behavior verification detects the regression
- **AND THEN** the implementation can reject that change even if some delegated compatibility commands still work

### Requirement: Pair-targeted install routes through `houmao-server`
Top-level `houmao-srv-ctrl install` SHALL route through `houmao-server` rather than mutating whichever ambient local `HOME` happens to be active.

At minimum, top-level `houmao-srv-ctrl install` SHALL target the selected public `houmao-server` listener by its configured or default base URL, and it SHALL verify the supported pair before performing the install.

The explicit compatibility command `houmao-srv-ctrl cao install` MAY remain available for raw local CAO-compatible install behavior, but that compatibility path SHALL be distinct from the canonical top-level pair install workflow.

#### Scenario: Top-level install uses the public pair authority
- **WHEN** an operator runs `houmao-srv-ctrl install projection-demo --provider codex`
- **THEN** `houmao-srv-ctrl` targets the selected `houmao-server` instance rather than performing a local raw CAO install by default
- **AND THEN** the install mutates that server's child-managed profile state without requiring the caller to know any hidden child-home path

#### Scenario: Compatibility install remains explicit and separate
- **WHEN** an operator intentionally wants raw CAO-compatible local install behavior
- **THEN** the operator uses `houmao-srv-ctrl cao install ...`
- **AND THEN** the canonical top-level install workflow remains Houmao-owned and pair-targeted
