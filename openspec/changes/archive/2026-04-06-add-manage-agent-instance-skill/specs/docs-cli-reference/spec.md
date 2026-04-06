## ADDED Requirements

### Requirement: System-skills reference documents the packaged agent-instance lifecycle skill and its boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-manage-agent-instance` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for managed-agent instance lifecycle guidance across:

- `agents launch`
- `project easy instance launch`
- `agents join`
- `agents list`
- `agents stop`
- `agents cleanup session|logs`

That page SHALL explain that `houmao-manage-agent-instance` complements rather than replaces `houmao-manage-specialist`.

That page SHALL explain that mailbox surfaces, mailbox cleanup, prompt/gateway control, and specialist CRUD remain outside the packaged `houmao-manage-agent-instance` skill scope.

That page SHALL describe the CLI-default system-skill install selection as including both the packaged specialist-management skill and the packaged agent-instance lifecycle skill.

#### Scenario: Reader sees the new packaged lifecycle skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-manage-agent-instance` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent instance lifecycle rather than specialist authoring

#### Scenario: Reader sees the boundary between the two packaged non-mailbox Houmao skills
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page distinguishes `houmao-manage-specialist` from `houmao-manage-agent-instance`
- **AND THEN** it does not imply that mailbox work or specialist CRUD belongs to the new lifecycle skill

#### Scenario: Reader sees the expanded CLI-default install outcome
- **WHEN** a reader checks the CLI-default selection behavior in `docs/reference/cli/system-skills.md`
- **THEN** the page explains that CLI-default installation includes both packaged non-mailbox Houmao skills
- **AND THEN** it does not imply that managed launch or managed join auto-install changed in the same way
