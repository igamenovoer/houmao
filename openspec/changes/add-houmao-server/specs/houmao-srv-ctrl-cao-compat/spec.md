## ADDED Requirements

### Requirement: `houmao-srv-ctrl` exposes a CAO-compatible command surface
The system SHALL expose a CAO-compatible command surface on a dedicated service-management binary named `houmao-srv-ctrl`.

For the supported `cao` version pinned by this change, `houmao-srv-ctrl` SHALL accept the same public command family, arguments, flags, exit-status semantics, and user-visible output shape closely enough to act as a drop-in replacement for operators switching from `cao` to `houmao-srv-ctrl`.

Aliasing `cao` to `houmao-srv-ctrl` SHALL work for the supported command family.

At minimum, the CAO-compatible command family SHALL include:

- `flow`
- `info`
- `init`
- `install`
- `launch`
- `mcp-server`
- `shutdown`

This change SHALL NOT repurpose the existing `houmao-cli` binary as the CAO-compatible service-management surface.

#### Scenario: Aliasing `cao` to `houmao-srv-ctrl` works for supported commands
- **WHEN** an operator aliases `cao` to `houmao-srv-ctrl` and invokes a supported `cao` command pattern
- **THEN** `houmao-srv-ctrl` accepts that command pattern with CAO-compatible behavior
- **AND THEN** the operator does not need a separate command rewrite layer just to switch to the Houmao-managed CLI

### Requirement: `houmao-srv-ctrl` compatibility is defined within the supported Houmao pair
The compatibility contract for `houmao-srv-ctrl` SHALL be defined as part of the supported `houmao-server + houmao-srv-ctrl` replacement pair for `cao-server + cao`.

This change SHALL NOT require `houmao-srv-ctrl` to support arbitrary external `cao-server` deployments as a public compatibility contract.

Mixed-pair usage such as `cao-server + houmao-srv-ctrl` SHALL be treated as unsupported in this change.

#### Scenario: Mixed raw-CAO-server-plus-`houmao-srv-ctrl` usage is not part of the compatibility promise
- **WHEN** an operator uses `houmao-srv-ctrl` against a raw `cao-server` deployment
- **THEN** that combination is outside the supported compatibility contract for this change
- **AND THEN** parity verification for the change does not need to claim that mixed pair works

### Requirement: Houmao extensions on `houmao-srv-ctrl` are additive only
When `houmao-srv-ctrl` extends an existing CAO-compatible command, those extensions SHALL be additive only.

Additive extensions MAY include:

- additional optional flags or arguments
- additional optional structured output fields where machine-readable output already exists
- additional new commands outside the supported CAO-compatible command family

`houmao-srv-ctrl` SHALL NOT require Houmao-only flags or arguments in order for a CAO-compatible invocation to succeed, and it SHALL NOT remove or repurpose CAO-defined command behavior for the supported compatibility family.

#### Scenario: CAO-compatible invocations work without Houmao-only flags
- **WHEN** an operator runs a supported CAO-compatible `houmao-srv-ctrl` command without any Houmao-only extension flags
- **THEN** `houmao-srv-ctrl` processes that invocation with CAO-compatible behavior
- **AND THEN** Houmao-only extensions remain optional rather than mandatory for compatibility

### Requirement: Most CAO-compatible CLI work delegates to the installed `cao` executable
For most CAO-compatible commands in the shallow cut, `houmao-srv-ctrl` SHALL call the installed `cao` executable internally rather than re-implementing CAO CLI behavior natively.

For delegated commands, `houmao-srv-ctrl` SHALL preserve CAO-facing behavior closely enough for practical drop-in use, including delegated exit status and user-visible output shape where feasible.

#### Scenario: Non-launch CAO-compatible command delegates to `cao`
- **WHEN** an operator invokes a CAO-compatible command such as `houmao-srv-ctrl install ...`
- **THEN** `houmao-srv-ctrl` may delegate that command to the installed `cao` executable internally
- **AND THEN** the operator receives the delegated command result through `houmao-srv-ctrl`

### Requirement: Agent-creating CLI flows register live agents with `houmao-server`
When a CAO-compatible `houmao-srv-ctrl` command creates or launches a live agent session, `houmao-srv-ctrl` SHALL register the resulting live agent with `houmao-server` after the delegated CAO operation succeeds.

For v1, successful `launch` commands SHALL satisfy this registration contract.

That registration SHALL supplement the delegated CAO behavior rather than replacing it in the shallow cut.

#### Scenario: Successful launch registers the live agent with `houmao-server`
- **WHEN** an operator runs a successful CAO-compatible `houmao-srv-ctrl launch ...`
- **THEN** `houmao-srv-ctrl` delegates the launch to `cao`
- **AND THEN** `houmao-srv-ctrl` also registers the resulting live agent or session with `houmao-server`
- **AND THEN** `houmao-server` can begin managing watch or state features for that launched agent

### Requirement: CLI-side registration does not require native Houmao launch ownership in v1
The shallow-cut CLI registration flow SHALL allow `houmao-server` to learn about agents launched through delegated CAO CLI behavior without requiring Houmao to own the full launch implementation natively.

Future native Houmao launch implementations MAY replace that delegation later without changing the public `houmao-srv-ctrl` compatibility name.

#### Scenario: Future native replacement does not require renaming the CLI
- **WHEN** a future version stops delegating `launch` to `cao`
- **THEN** the public command remains `houmao-srv-ctrl launch`
- **AND THEN** operators do not need to switch back to `cao` naming to use the evolved Houmao implementation

### Requirement: `houmao-srv-ctrl` compatibility SHALL be verified against a real `cao` CLI
The implementation SHALL include verification that exercises the supported `cao` command family against both `cao` and `houmao-srv-ctrl` and compares the compatibility-significant results.

That verification SHALL cover at minimum:

- command acceptance and argument parsing
- exit status behavior
- user-visible output shape for supported commands
- successful live-agent launch registration for commands that create live agents

#### Scenario: CLI compatibility verification catches non-additive divergences
- **WHEN** a `houmao-srv-ctrl` compatibility command changes in a way that breaks a CAO-compatible invocation or CAO-defined CLI contract
- **THEN** parity verification against a real `cao` CLI detects the divergence
- **AND THEN** the implementation can reject that change before claiming drop-in CLI compatibility
