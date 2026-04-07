## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-manage-agent-instance` system skill
The system SHALL package a Houmao-owned system skill named `houmao-manage-agent-instance` under the maintained system-skill asset root.

That skill SHALL instruct agents to manage live managed-agent instances through these supported lifecycle commands:

- `houmao-mgr agents launch`
- `houmao-mgr project easy instance launch`
- `houmao-mgr agents join`
- `houmao-mgr agents list`
- `houmao-mgr agents stop`
- `houmao-mgr agents cleanup session`
- `houmao-mgr agents cleanup logs`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `launch`
- `join`
- `list`
- `stop`
- `cleanup`

That packaged skill SHALL remain the canonical Houmao-owned skill for general live managed-agent lifecycle guidance even when `houmao-manage-specialist` also offers specialist-scoped `launch` and `stop` entry points with post-action handoff into this skill.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `project easy specialist create|list|get|remove`
- `project easy instance list|get|stop`
- `agents prompt`, `agents interrupt`, `agents relaunch`, `agents turn`, and `agents gateway ...`
- `agents mailbox ...`, `agents mail ...`, and `agents cleanup mailbox`
- `project mailbox ...` and `admin cleanup runtime ...`

#### Scenario: Installed skill points the agent at instance lifecycle commands
- **WHEN** an agent opens the installed `houmao-manage-agent-instance` skill
- **THEN** the skill directs the agent to use the supported launch, join, list, stop, and cleanup commands for managed-agent instances
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing or unrelated runtime-control surfaces

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-manage-agent-instance` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `launch`, `join`, `list`, `stop`, and `cleanup`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

#### Scenario: Installed skill keeps mailbox and specialist CRUD out of scope
- **WHEN** an agent reads the installed `houmao-manage-agent-instance` skill
- **THEN** the skill marks mailbox operations and specialist CRUD as outside the packaged skill scope
- **AND THEN** it does not present those actions as part of managed-agent instance lifecycle guidance

#### Scenario: Installed skill remains the follow-up lifecycle surface after specialist-scoped entry
- **WHEN** an agent or user reaches `houmao-manage-agent-instance` after using specialist-scoped `launch` or `stop` guidance
- **THEN** the skill remains the canonical packaged Houmao-owned entry point for further live managed-agent lifecycle work
- **AND THEN** it does not require `houmao-manage-specialist` to become a general-purpose instance-management skill
