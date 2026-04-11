## ADDED Requirements

### Requirement: System-skills reference documents the generic loop planner replacement
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-agent-loop-generic` as a packaged Houmao-owned system skill.

That page SHALL describe `houmao-agent-loop-generic` as the generic composed-loop planner and `start|status|stop` run-control skill for user-controlled agents that need to decompose a communication graph into pairwise local-close components and relay-root components.

That page SHALL explain that `houmao-agent-loop-generic` replaces the prior relay-only `houmao-agent-loop-relay` packaged skill.

When the page describes current install selections that expand `user-control`, it SHALL enumerate `houmao-agent-loop-generic` when it is present in the packaged catalog and SHALL NOT enumerate `houmao-agent-loop-relay` as current after the catalog replacement.

#### Scenario: Reader sees the generic loop planner in the system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-agent-loop-generic` as a packaged Houmao-owned skill
- **AND THEN** it describes generic pairwise/relay graph decomposition rather than relay-only planning

#### Scenario: Reader sees generic loop skill in current install selections
- **WHEN** a reader checks the current packaged inventory or install-selection behavior in `docs/reference/cli/system-skills.md`
- **THEN** the page lists `houmao-agent-loop-generic` when the packaged catalog includes it
- **AND THEN** the page does not list `houmao-agent-loop-relay` as a current installable skill after the replacement
