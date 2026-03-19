## ADDED Requirements

### Requirement: `houmao-cli` exposes a CAO-compatible command surface
The system SHALL expose a CAO-compatible command surface on `houmao-cli`.

For the targeted CAO version supported by this change, `houmao-cli` SHALL accept the same top-level CAO command family closely enough to act as a drop-in replacement for operators switching from `cao` to `houmao-cli`.

At minimum, the CAO-compatible command family SHALL include:

- `flow`
- `info`
- `init`
- `install`
- `launch`
- `mcp-server`
- `shutdown`

The existing Houmao runtime-management command family on `houmao-cli` SHALL remain available in parallel.

#### Scenario: CAO-compatible launch vocabulary is accepted on `houmao-cli`
- **WHEN** an operator invokes `houmao-cli launch` using the targeted CAO-compatible option pattern
- **THEN** `houmao-cli` accepts that CAO-compatible command family on the same binary
- **AND THEN** the existing Houmao runtime-management subcommands remain available as separate commands

### Requirement: Most CAO-compatible CLI work delegates to the installed `cao` executable
For most CAO-compatible commands in the shallow cut, `houmao-cli` SHALL call the installed `cao` executable internally rather than re-implementing CAO CLI behavior natively.

For delegated commands, `houmao-cli` SHALL preserve CAO-facing behavior closely enough for practical drop-in use, including delegated exit status and user-visible output shape where feasible.

#### Scenario: Non-launch CAO-compatible command delegates to `cao`
- **WHEN** an operator invokes a CAO-compatible command such as `houmao-cli install ...`
- **THEN** `houmao-cli` may delegate that command to the installed `cao` executable internally
- **AND THEN** the operator receives the delegated command result through `houmao-cli`

### Requirement: Agent-creating CLI flows register live agents with `houmao-server`
When a CAO-compatible `houmao-cli` command creates or launches a live agent session, `houmao-cli` SHALL register the resulting live agent with `houmao-server` after the delegated CAO operation succeeds.

For v1, successful `launch` commands SHALL satisfy this registration contract.

That registration SHALL supplement the delegated CAO behavior rather than replacing it in the shallow cut.

#### Scenario: Successful launch registers the live agent with `houmao-server`
- **WHEN** an operator runs a successful CAO-compatible `houmao-cli launch ...`
- **THEN** `houmao-cli` delegates the launch to `cao`
- **AND THEN** `houmao-cli` also registers the resulting live agent or session with `houmao-server`
- **AND THEN** `houmao-server` can begin managing watch or state features for that launched agent

### Requirement: CLI-side registration does not require native Houmao launch ownership in v1
The shallow-cut CLI registration flow SHALL allow `houmao-server` to learn about agents launched through delegated CAO CLI behavior without requiring Houmao to own the full launch implementation natively.

Future native Houmao launch implementations MAY replace that delegation later without changing the public `houmao-cli` compatibility name.

#### Scenario: Future native replacement does not require renaming the CLI
- **WHEN** a future version stops delegating `launch` to `cao`
- **THEN** the public command remains `houmao-cli launch`
- **AND THEN** operators do not need to switch back to `cao` naming to use the evolved Houmao implementation
