## MODIFIED Requirements

### Requirement: System-skills reference documents the renamed specialist-management skill
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe the current project-easy packaged skill as `houmao-manage-specialist`.

That page SHALL describe the packaged skill as the Houmao-owned specialist-management entry point for `project easy specialist create|list|get|remove` plus specialist-scoped `project easy instance launch|stop`.

The page SHALL describe the top-level packaged skill page as an index/router and SHALL state that further agent management after those specialist-scoped runtime actions goes to `houmao-manage-agent-instance`.

The page SHALL NOT continue to describe `houmao-create-specialist` as the active packaged project-easy skill.

#### Scenario: Reader sees the renamed packaged skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-manage-specialist` as the packaged project-easy skill
- **AND THEN** it describes that skill as covering `create`, `list`, `get`, `remove`, `launch`, and `stop`

#### Scenario: Reader does not see the stale create-only packaged skill name
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page does not present `houmao-create-specialist` as the current packaged specialist-management skill
- **AND THEN** it explains that follow-up live-agent management after specialist launch or stop belongs to `houmao-manage-agent-instance`

### Requirement: System-skills reference documents the packaged agent-instance lifecycle skill and its boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-manage-agent-instance` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for managed-agent instance lifecycle guidance across:

- `agents launch`
- `project easy instance launch`
- `agents join`
- `agents list`
- `agents stop`
- `agents cleanup session|logs`

That page SHALL explain that `houmao-manage-agent-instance` remains the canonical follow-up lifecycle skill even though `houmao-manage-specialist` now also covers specialist-scoped `launch` and `stop`.

That page SHALL explain that mailbox surfaces, mailbox cleanup, prompt/gateway control, and specialist CRUD remain outside the packaged `houmao-manage-agent-instance` skill scope.

That page SHALL describe the CLI-default system-skill install selection as including both the packaged specialist-management skill and the packaged agent-instance lifecycle skill.

#### Scenario: Reader sees the new packaged lifecycle skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-manage-agent-instance` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering managed-agent instance lifecycle rather than specialist authoring

#### Scenario: Reader sees the boundary between the two packaged non-mailbox Houmao skills
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page distinguishes `houmao-manage-specialist` from `houmao-manage-agent-instance`
- **AND THEN** it explains that specialist launch and stop can start in the former while broader follow-up lifecycle work belongs to the latter

#### Scenario: Reader sees the expanded CLI-default install outcome
- **WHEN** a reader checks the CLI-default selection behavior in `docs/reference/cli/system-skills.md`
- **THEN** the page explains that CLI-default installation includes both packaged non-mailbox Houmao skills
- **AND THEN** it does not imply that managed launch or managed join auto-install changed in the same way
