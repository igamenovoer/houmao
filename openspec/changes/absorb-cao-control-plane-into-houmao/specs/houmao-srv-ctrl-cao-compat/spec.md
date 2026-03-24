## ADDED Requirements

### Requirement: Session-backed compatibility commands use Houmao-owned pair authority
When a supported `houmao-srv-ctrl cao ...` command creates, inspects, mutates, or shuts down a session in the supported pair, `houmao-srv-ctrl` SHALL execute that behavior through Houmao-owned pair APIs rather than through an external `cao` subprocess.

This requirement applies at minimum to `houmao-srv-ctrl cao launch`, `houmao-srv-ctrl cao info`, `houmao-srv-ctrl cao shutdown`, and `houmao-srv-ctrl cao install`.

#### Scenario: Namespaced compatibility launch uses the pair authority directly
- **WHEN** an operator runs `houmao-srv-ctrl cao launch ...` against the supported pair
- **THEN** `houmao-srv-ctrl` launches the session through Houmao-owned pair authority
- **AND THEN** it does not shell out to an external `cao` executable to complete the launch

#### Scenario: Namespaced compatibility info stays within the supported pair
- **WHEN** an operator runs `houmao-srv-ctrl cao info`
- **THEN** `houmao-srv-ctrl` reads compatibility-significant session information through Houmao-owned pair authority
- **AND THEN** the command does not require a raw `cao-server` deployment as its supported target

## MODIFIED Requirements

### Requirement: Most CAO-compatible CLI work delegates to the installed `cao` executable
The supported `houmao-srv-ctrl cao ...` command family SHALL be implemented by Houmao-owned compatibility code rather than by delegating to an installed `cao` executable.

For session-backed compatibility commands, `houmao-srv-ctrl` SHALL use pair-aware implementations over the supported `houmao-server` boundary.

For local-only compatibility commands that remain part of the documented command family, `houmao-srv-ctrl` SHALL use Houmao-owned compatibility helpers rather than shelling out to external `cao`.

The supported pair SHALL NOT require `cao` to be installed on `PATH` in order for the documented `houmao-srv-ctrl cao ...` surface to work.

#### Scenario: Local-only compatibility command works without installed `cao`
- **WHEN** an operator invokes a documented local-only compatibility command such as `houmao-srv-ctrl cao flow list`
- **THEN** `houmao-srv-ctrl` satisfies that command through Houmao-owned compatibility code
- **AND THEN** the operator does not need `cao` installed on `PATH`

#### Scenario: Server-backed compatibility command uses a pair-aware wrapper
- **WHEN** an operator invokes a server-backed compatibility command such as `houmao-srv-ctrl cao info`
- **THEN** `houmao-srv-ctrl` satisfies that CAO-compatible UX through a repo-owned pair-aware implementation
- **AND THEN** the command does not depend on blind subprocess passthrough to remain part of the supported compatibility surface

### Requirement: `houmao-srv-ctrl` compatibility SHALL be verified against a real `cao` CLI
The implementation SHALL include verification that compares the explicit `houmao-srv-ctrl cao ...` command surface to the pinned CAO source and exercises the compatibility commands through the Houmao-owned implementations that replace external `cao` delegation.

Where a real CAO CLI invocation remains the most direct parity oracle, verification MAY use it as an oracle. The supported product path SHALL NOT depend on that CLI being present.

That compatibility verification SHALL cover at minimum:

- command availability under the `cao` namespace
- argument parsing for the CAO-compatible command family
- script-facing exit-code and machine-readable output behavior
- pair-aware wrapper behavior where explicit pair routing replaces external `cao`
- local compatibility-helper behavior for namespaced commands that remain local-only
- supported-pair enforcement where Houmao intentionally rejects mixed-pair usage

Houmao-owned CLI behavior SHALL be tested directly and more strictly. That verification SHALL cover at minimum:

- native headless top-level `launch --headless`
- session-backed top-level `launch` registration and runtime artifact materialization
- namespaced compatibility launch/info/shutdown/install through the pair
- top-level `install` routing through `houmao-server`

#### Scenario: Compatibility verification catches namespace regressions
- **WHEN** a `houmao-srv-ctrl cao` command changes in a way that breaks CAO-compatible invocation shape or compatibility-significant behavior
- **THEN** compatibility verification detects the divergence
- **AND THEN** the implementation can reject that change before claiming namespaced CAO compatibility

#### Scenario: Houmao-owned verification catches pair-command regressions
- **WHEN** a top-level or namespaced Houmao-owned command changes in a way that breaks pair launch, install, or compatibility-wrapper behavior
- **THEN** direct Houmao behavior verification detects the regression
- **AND THEN** the implementation can reject that change even though no external `cao` subprocess is involved

### Requirement: Pair-targeted install routes through `houmao-server`
Top-level `houmao-srv-ctrl install` SHALL route through `houmao-server` rather than mutating whichever ambient local `HOME` happens to be active.

At minimum, top-level `houmao-srv-ctrl install` SHALL target the selected public `houmao-server` listener by its configured or default base URL, and it SHALL verify the supported pair before performing the install.

The explicit compatibility command `houmao-srv-ctrl cao install` SHALL preserve the CAO-compatible invocation shape but SHALL resolve through the same Houmao-owned compatibility install authority rather than requiring a raw local CAO install path.

#### Scenario: Top-level install uses the public pair authority
- **WHEN** an operator runs `houmao-srv-ctrl install projection-demo --provider codex`
- **THEN** `houmao-srv-ctrl` targets the selected `houmao-server` instance rather than performing a local raw CAO install
- **AND THEN** the install mutates that server's Houmao-managed compatibility profile state without requiring the caller to know any hidden storage path

#### Scenario: Namespaced compatibility install keeps CAO shape without external CAO state
- **WHEN** an operator runs `houmao-srv-ctrl cao install projection-demo --provider codex`
- **THEN** `houmao-srv-ctrl` accepts the CAO-compatible command shape
- **AND THEN** the implementation resolves that install through Houmao-owned compatibility install behavior instead of mutating an external CAO home

## REMOVED Requirements

### Requirement: CLI-side registration does not require native Houmao launch ownership in v1
**Reason**: The supported `houmao-srv-ctrl cao` launch path now uses Houmao-owned compatibility implementations instead of delegated CAO CLI behavior.
**Migration**: Keep using `houmao-srv-ctrl launch ...` or `houmao-srv-ctrl cao launch ...` in the supported pair, but do not assume those commands delegate to an external `cao` binary.
