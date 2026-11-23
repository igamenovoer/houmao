# houmao-managed-agent-self-identity Specification

## Purpose
TBD - created by archiving change add-managed-agent-instance-state. Update Purpose after archive.
## Requirements
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

### Requirement: Untrusted context cannot claim managed self
Prompt text, cwd names, caller-supplied agent names, and an unverified environment pointer SHALL not establish self authority.

#### Scenario: Unmanaged shell copies an agent name
- **WHEN** an unmanaged process invokes a self command with a known agent name in its prompt or cwd
- **THEN** Houmao SHALL reject the request

### Requirement: Self verification rejects stale runtime generations
Every self operation SHALL verify that manifest identity, project, runtime binding, and generation match the current live registry record.

#### Scenario: Preserved old process uses a stale manifest
- **WHEN** the registry has advanced beyond the manifest generation
- **THEN** Houmao SHALL reject self resolution without reading instance state
