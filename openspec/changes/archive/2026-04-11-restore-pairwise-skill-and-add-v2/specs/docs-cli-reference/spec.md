## ADDED Requirements

### Requirement: System-skills reference documents both pairwise skill variants and their boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` as packaged Houmao-owned system skills.

That page SHALL describe `houmao-agent-loop-pairwise` as the restored stable pairwise skill for manual pairwise planning plus `start|status|stop` run control.

That page SHALL describe `houmao-agent-loop-pairwise-v2` as the manual-invocation-only versioned enriched pairwise skill for authoring, prestart, and expanded run control.

That page SHALL explain that the stable and v2 pairwise skills are distinct packaged choices rather than aliases for the same skill.

When the page describes current install selections that expand `user-control`, it SHALL enumerate both pairwise skill variants when both are present in the packaged catalog.

#### Scenario: Reader sees both pairwise variants in the system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` as packaged Houmao-owned skills
- **AND THEN** it explains the stable-versus-v2 boundary instead of presenting the two names as interchangeable aliases

#### Scenario: Reader sees both pairwise variants in current install selections
- **WHEN** a reader checks the current packaged inventory or install-selection behavior in `docs/reference/cli/system-skills.md`
- **THEN** the page lists both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` when the packaged catalog includes both
- **AND THEN** the page explains that both arrive through `user-control` when that set contains both
