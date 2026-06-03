## ADDED Requirements

### Requirement: Pairwise-v4 legacy guidance names current scoped memory surfaces
The retired packaged `houmao-agent-loop-pairwise-v4` skill SHALL NOT route managed-memory work through removed root-level `houmao-mgr agents memory ...` command shapes.

When legacy v4 guidance mentions maintained CLI memory surfaces, it SHALL name or delegate to current `houmao-memory-mgr` guidance for `houmao-mgr agents self memory ...` and `houmao-mgr agents single --agent-name|--agent-id ... memory ...`.

#### Scenario: Legacy v4 memory routing avoids removed agents memory shorthand
- **WHEN** a caller reads the retired pairwise-v4 skill routing guidance for managed-memory reads or writes
- **THEN** the guidance routes through `houmao-memory-mgr` and current scoped memory surfaces
- **AND THEN** it does not name `houmao-mgr agents memory ...` as a supported command family
