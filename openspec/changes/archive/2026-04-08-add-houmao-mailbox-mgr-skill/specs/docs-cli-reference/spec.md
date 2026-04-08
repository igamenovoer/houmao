## ADDED Requirements

### Requirement: System-skills reference documents the packaged `houmao-mailbox-mgr` skill and its mailbox-admin boundary
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-mailbox-mgr` as a packaged Houmao-owned system skill.

That page SHALL describe the packaged skill as the Houmao-owned entry point for mailbox-administration guidance across:

- `houmao-mgr mailbox ...`
- `houmao-mgr project mailbox ...`
- `houmao-mgr agents mailbox ...`

That page SHALL explain that `houmao-mailbox-mgr` covers filesystem mailbox root lifecycle, mailbox account lifecycle, structural mailbox inspection, and late filesystem mailbox binding for existing local managed agents.

That page SHALL explain that ordinary mailbox participation remains in `houmao-agent-email-comms`, notifier-driven unread-email rounds remain in `houmao-process-emails-via-gateway`, and gateway mail-notifier control remains in `houmao-agent-gateway`.

That page SHALL explain that the maintained mailbox-admin CLI remains filesystem-oriented in v1 and that Stalwart stays a transport/bootstrap boundary rather than a peer mailbox-admin CLI family.

#### Scenario: Reader sees the packaged mailbox-admin skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-mailbox-mgr` as a packaged Houmao-owned skill
- **AND THEN** it describes that skill as covering mailbox administration across mailbox, project mailbox, and agents mailbox surfaces

#### Scenario: Reader sees the boundary between mailbox admin and mailbox participation
- **WHEN** a reader opens the packaged mailbox-admin skill section of `docs/reference/cli/system-skills.md`
- **THEN** the page distinguishes mailbox root and binding administration from ordinary mailbox send/check/reply work
- **AND THEN** it does not imply that `houmao-mailbox-mgr` replaces `houmao-agent-email-comms`, `houmao-process-emails-via-gateway`, or `houmao-agent-gateway`
