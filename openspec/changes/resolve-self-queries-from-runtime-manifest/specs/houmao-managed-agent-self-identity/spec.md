# Spec Delta

## MODIFIED Requirements

### Requirement: Verified self resolves from current runtime authority
Houmao SHALL resolve managed self from a confined runtime manifest and the current shared-registry generation. The manifest SHALL supply the agent's identity fields. Tmux-backed self resolution SHALL verify the owning socket and session. Supported headless runtimes SHALL also resolve self through their runtime-owned manifest locator.

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
