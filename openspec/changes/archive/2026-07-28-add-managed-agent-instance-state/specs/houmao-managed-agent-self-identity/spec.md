## ADDED Requirements

### Requirement: Verified self resolves from current runtime authority
Houmao SHALL resolve managed self from a confined runtime manifest and the current shared-registry generation. Tmux presence SHALL not be required for supported headless runtimes.

#### Scenario: Headless managed agent resolves self
- **WHEN** a headless agent presents its runtime-owned manifest pointer and the manifest matches one current live registry record
- **THEN** verified-self commands SHALL resolve that opaque managed-agent identity

#### Scenario: Tmux managed agent resolves self
- **WHEN** a tmux-backed agent presents matching manifest, registry, and tmux bindings
- **THEN** verified-self commands SHALL resolve the same opaque managed-agent identity

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
