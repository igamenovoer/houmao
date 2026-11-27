# Spec Delta

## MODIFIED Requirements

### Requirement: Verified self resolves from current runtime authority

Houmao SHALL resolve managed self from a confined runtime manifest and the current shared-registry generation. The manifest SHALL supply the agent's identity fields. Tmux self resolution SHALL verify the owning socket and session. Supported headless runtimes SHALL resolve self through their runtime-owned manifest locator. A Hermes named-profile tool SHALL also prove native origin tied to its exact profile, session, and current managed generation.

#### Scenario: Headless managed agent resolves self

- **WHEN** a headless agent presents its runtime-owned manifest pointer and the manifest matches one current live registry record
- **THEN** verified-self commands resolve that opaque managed-agent identity even when tmux is absent, subject to the selected backend's caller-origin check

#### Scenario: Tmux managed agent resolves self

- **WHEN** a tmux-backed agent presents matching manifest, registry, and tmux bindings
- **THEN** verified-self commands resolve the same opaque managed-agent identity
- **AND THEN** the identity query succeeds with the agent definition directory unavailable

#### Scenario: A detached Web shell locates its owner

- **WHEN** a managed Web tool shell has a runtime-provided binding to its owning tmux session and `TMUX` is empty
- **THEN** self lookup uses that bound socket and session to locate the manifest
- **AND THEN** it accepts only the matching live generation

#### Scenario: A Detached Hermes Tool Resolves Its Own Runtime

- **WHEN** a tool of a current managed Hermes worker presents native execution-origin evidence for the recorded gateway incarnation, served profile, session, and managed generation
- **THEN** self commands resolve that current managed identity without requiring tmux or a live terminal view
- **AND THEN** the manifest, registry, and native binding agree before self credentials can be used

#### Scenario: A Verified Same-Home Daemon Has No Houmao Launch Environment

- **WHEN** a still-current standalone worker with retained ownership uses an already verified exact-home daemon
- **THEN** a tool of that standalone daemon can locate and prove its existing managed generation without launch-supplied Houmao variables

#### Scenario: A Locator Cannot Substitute for Daemon Proof

- **WHEN** a shell, sibling worker with the same gateway PID, or stale tool presents a copied home, link, session identifier, or manifest locator
- **THEN** self resolution refuses any caller without verified origin for the selected profile, session, and current managed generation
- **AND THEN** a missing or mismatched proof fails without starting a gateway, signing for another identity, or retrying without proof

#### Scenario: Native Profile Authority Has Changed

- **WHEN** the shared gateway is replaced, the selected profile is unserved and re-served, or the worker generation ends
- **THEN** old tool-origin evidence cannot authorize self on the current worker
- **AND THEN** qualified tools from the current binding can obtain fresh evidence for that binding
