## ADDED Requirements

### Requirement: `houmao-srv-ctrl` exposes a CAO-compatible command surface
The system SHALL expose a CAO-compatible command surface on a dedicated service-management binary named `houmao-srv-ctrl`.

For the supported `cao` version pinned by this change, `houmao-srv-ctrl` SHALL accept the same public command family, arguments, and flags closely enough to act as a drop-in replacement for operators switching from `cao` to `houmao-srv-ctrl`.

For commands that remain delegated to the installed `cao` executable in v1, the downstream business behavior remains CAO-owned. This change's CLI contract focuses on command acceptance, delegation wiring, supported-pair enforcement, and Houmao-owned post-launch behavior rather than redefining the full downstream `cao` implementation.

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

### Requirement: `houmao-srv-ctrl` compatibility is pinned to one exact CAO source of truth
For this change, the CAO CLI compatibility source of truth SHALL be pinned to:

- repository: `https://github.com/imsight-forks/cli-agent-orchestrator.git`
- commit: `0fb3e5196570586593736a21262996ca622f53b6`
- local tracked checkout: `extern/tracked/cli-agent-orchestrator`

The change SHALL treat that exact source as the parity oracle for `houmao-srv-ctrl` CLI compatibility rather than a floating branch name or whichever `cao` happens to be on `PATH`.

#### Scenario: CLI parity verification uses the pinned CAO source
- **WHEN** implementation or verification compares `houmao-srv-ctrl` behavior to CAO CLI behavior
- **THEN** it uses the pinned CAO source of truth for this change
- **AND THEN** the parity target does not drift with a floating upstream branch

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

For delegated commands, `houmao-srv-ctrl` SHALL preserve command acceptance and delegation wiring closely enough for practical drop-in use, including argument forwarding into `cao` and delegated process completion behavior where feasible.

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

### Requirement: Successful delegated launches materialize Houmao-owned authoritative session artifacts
When `houmao-srv-ctrl launch` succeeds through delegated CAO behavior inside the supported Houmao pair, it SHALL materialize Houmao-owned authoritative session artifacts for that launched session rather than leaving the launch server-only.

At minimum, that materialization SHALL:

- create or update a Houmao runtime-owned session root
- write a runtime-owned manifest that uses `backend = "houmao_server_rest"`
- let any transitional shared-registry publication point back to that manifest and session root
- keep later gateway and mailbox follow-up flows able to reuse those manifest-backed artifacts while those subsystems still depend on runtime-owned manifests

#### Scenario: Delegated launch writes a Houmao-owned manifest for later reuse
- **WHEN** an operator runs a successful `houmao-srv-ctrl launch ...`
- **THEN** `houmao-srv-ctrl` materializes a Houmao-owned session root and manifest for that launched session
- **AND THEN** later discovery, gateway, or mailbox follow-up flows can point back to those artifacts instead of depending on a separate server-only truth

### Requirement: CLI-side registration does not require native Houmao launch ownership in v1
The shallow-cut CLI registration flow SHALL allow `houmao-server` to learn about agents launched through delegated CAO CLI behavior without requiring Houmao to own the full launch implementation natively.

Future native Houmao launch implementations MAY replace that delegation later without changing the public `houmao-srv-ctrl` compatibility name.

#### Scenario: Future native replacement does not require renaming the CLI
- **WHEN** a future version stops delegating `launch` to `cao`
- **THEN** the public command remains `houmao-srv-ctrl launch`
- **AND THEN** operators do not need to switch back to `cao` naming to use the evolved Houmao implementation

### Requirement: `houmao-srv-ctrl` compatibility SHALL be verified against a real `cao` CLI
The implementation SHALL include verification that uses the pinned `cao` source and delegated invocation patterns to exercise the supported command family through `houmao-srv-ctrl`.

For delegated passthrough commands, verification SHALL focus on whether `houmao-srv-ctrl` accepts the CAO-compatible command pattern and forwards the invocation into `cao` correctly.

That delegated-command verification SHALL cover at minimum:

- command acceptance and argument parsing
- argv forwarding into delegated `cao` invocations
- supported-pair enforcement where Houmao intentionally rejects mixed-pair usage

That delegated-command verification SHALL NOT require byte-for-byte stdout or stderr parity or full re-testing of downstream `cao` command behavior once the delegated invocation is accepted.

Houmao-owned CLI behavior SHALL be tested directly and more strictly. That verification SHALL cover at minimum:

- successful live-agent launch registration for `launch`
- Houmao-owned runtime artifact materialization for delegated launches
- additive post-launch behavior implemented by `houmao-srv-ctrl`

#### Scenario: Delegated CLI verification catches command-surface regressions
- **WHEN** a delegated `houmao-srv-ctrl` command changes in a way that breaks a CAO-compatible invocation shape or delegation wiring
- **THEN** delegated-command verification detects the divergence
- **AND THEN** the implementation can reject that change before claiming compatibility-safe delegation

#### Scenario: Houmao-owned launch verification catches post-launch regressions
- **WHEN** the Houmao-owned `launch` follow-up logic changes in a way that breaks registration or runtime artifact materialization
- **THEN** direct Houmao behavior verification detects the regression
- **AND THEN** the implementation can reject that change even if delegated `cao launch` still accepts the invocation
