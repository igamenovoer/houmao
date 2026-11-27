# Spec Delta

## MODIFIED Requirements

### Requirement: Verified self resolves from current runtime authority
Houmao SHALL resolve managed self from a confined runtime manifest and the current shared-registry generation. The manifest SHALL supply the agent's identity fields. Tmux self resolution SHALL verify the owning socket and session. Supported headless runtimes SHALL resolve self through their runtime-owned manifest locator. Detached Hermes service and TUI callers SHALL prove descent from the recorded native daemon for the current managed generation.

#### Scenario: Headless managed agent resolves self
- **WHEN** a headless agent presents its runtime-owned manifest pointer and the manifest matches one current live registry record
- **THEN** verified-self commands resolve that opaque managed-agent identity even when tmux is absent

#### Scenario: Tmux managed agent resolves self
- **WHEN** a tmux-backed agent presents matching manifest, registry, and tmux bindings
- **THEN** verified-self commands resolve the same opaque managed-agent identity
- **AND THEN** the identity query succeeds with the agent definition directory unavailable

#### Scenario: A detached Web shell locates its owner
- **WHEN** a managed Web tool shell has a runtime-provided binding to its owning tmux session and `TMUX` is empty
- **THEN** self lookup uses that bound socket and session to locate the manifest
- **AND THEN** it accepts only the matching live generation

#### Scenario: A Detached Hermes Tool Resolves Its Own Runtime

- **WHEN** a tool process descends from the verified daemon of a current managed Hermes service or TUI
- **THEN** self commands resolve the current managed identity without requiring tmux
- **AND THEN** the daemon proof matches the current owner's recorded process incarnation and managed home
- **AND THEN** any recorded native session binding agrees with the managed runtime

#### Scenario: A Verified Same-Home Daemon Has No Houmao Launch Environment

- **WHEN** Houmao adopts and verifies the daemon for the exact managed Hermes home through a supported lifecycle operation
- **THEN** its tools can locate and prove the current managed generation without launch-supplied Houmao variables

#### Scenario: A Locator Cannot Substitute for Daemon Proof

- **WHEN** a shell, another agent, or a stale tool process presents a copied or stale Hermes locator
- **THEN** self resolution refuses a caller outside the verified current daemon lineage or a caller bound to an older generation
- **AND THEN** a missing, unsafe, or mismatched record fails without starting a daemon or selecting another runtime
