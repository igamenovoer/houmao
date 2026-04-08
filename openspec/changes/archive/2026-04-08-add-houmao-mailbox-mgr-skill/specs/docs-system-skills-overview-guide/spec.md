## ADDED Requirements

### Requirement: System-skills overview guide includes the packaged mailbox-admin skill and mailbox set distinction
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-mailbox-mgr` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-mailbox-mgr` as the mailbox-administration skill for mailbox root lifecycle, mailbox account lifecycle, structural mailbox inspection, and late managed-agent filesystem mailbox binding.

When the guide explains the named sets, it SHALL distinguish `mailbox-core` from `mailbox-full` by describing `mailbox-core` as the narrow mailbox worker pair and `mailbox-full` as the broader mailbox set that also includes `houmao-mailbox-mgr`.

#### Scenario: Reader sees the packaged mailbox-admin skill in the narrative guide
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-mailbox-mgr` among the shipped packaged system skills
- **AND THEN** it describes that skill as the mailbox-administration entrypoint rather than as the ordinary mailbox-operations skill

#### Scenario: Reader sees that `mailbox-full` is broader than `mailbox-core`
- **WHEN** a reader checks the named-set explanation in the system-skills overview guide
- **THEN** the guide explains that `mailbox-core` is the narrow mailbox worker pair
- **AND THEN** it explains that `mailbox-full` also includes `houmao-mailbox-mgr`
