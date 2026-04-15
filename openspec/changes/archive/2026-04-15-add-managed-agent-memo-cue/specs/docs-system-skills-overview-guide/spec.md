## ADDED Requirements

### Requirement: System-skills overview guide includes the packaged memory-management skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-memory-mgr` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-memory-mgr` as the managed-memory skill for reading, editing, appending, pruning, and organizing the fixed `houmao-memo.md` file and contained `pages/` files through supported Houmao memory surfaces.

When the guide explains named sets and default installation, it SHALL mention the dedicated managed-memory set and SHALL state that managed launch, managed join, and CLI-default installation include `houmao-memory-mgr` through that set.

#### Scenario: Reader sees the packaged memory-management skill in the narrative guide
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-memory-mgr` among the shipped packaged system skills
- **AND THEN** it describes that skill as the managed memo and pages editing entrypoint

#### Scenario: Reader sees memory-management auto-install behavior
- **WHEN** a reader checks the named-set or auto-install explanation in the system-skills overview guide
- **THEN** the guide explains that the managed-memory set includes `houmao-memory-mgr`
- **AND THEN** it explains that managed launch, managed join, and CLI-default installation include that set

