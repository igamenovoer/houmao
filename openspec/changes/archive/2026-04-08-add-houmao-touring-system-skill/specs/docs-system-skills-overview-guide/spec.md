## ADDED Requirements

### Requirement: System-skills overview guide lists the manual guided touring skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-touring` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-touring` as the manual guided-tour skill for first-time or re-orienting users. That description SHALL explain that the skill orients on current state and helps the user branch across project setup, mailbox setup, specialist/profile authoring, agent launch, post-launch operations, and lifecycle follow-up.

The guide SHALL state that `houmao-touring` is manual-invocation-only and SHALL NOT present it as the default routing choice for ordinary direct-operation requests.

When the guide explains the packaged named sets or default install selections, it SHALL mention the dedicated `touring` named set.

#### Scenario: Reader sees the touring skill in the narrative guide
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-touring` among the packaged Houmao-owned system skills
- **AND THEN** it describes the skill as a guided first-user tour rather than as a direct-operation skill

#### Scenario: Reader sees that touring is manual-only and branching
- **WHEN** a reader checks the `houmao-touring` entry in the narrative guide
- **THEN** the guide explains that the skill is manual-invocation-only
- **AND THEN** it explains that the tour can revisit branches such as creating more specialists, launching more agents, or following up with stop, relaunch, or cleanup
