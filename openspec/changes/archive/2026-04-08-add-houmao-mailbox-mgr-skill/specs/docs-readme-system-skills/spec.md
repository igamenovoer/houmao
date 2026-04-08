## ADDED Requirements

### Requirement: README system-skills subsection lists the packaged mailbox-admin skill
The `README.md` system-skills subsection SHALL list `houmao-mailbox-mgr` as one of the current packaged skill families.

That catalog row or list entry SHALL describe `houmao-mailbox-mgr` as the mailbox-administration skill for mailbox root lifecycle, mailbox account lifecycle, structural mailbox inspection, and late managed-agent filesystem mailbox binding.

That subsection SHALL distinguish `houmao-mailbox-mgr` from `houmao-agent-email-comms` and `houmao-process-emails-via-gateway` by explaining that the new skill handles mailbox administration while the existing mailbox skills handle ordinary mailbox participation and notifier-driven unread-mail rounds.

#### Scenario: Reader sees the packaged mailbox-admin skill in the README catalog
- **WHEN** a reader scans the README system-skills catalog table or list
- **THEN** they find `houmao-mailbox-mgr` with a one-line description
- **AND THEN** the entry describes mailbox administration rather than ordinary mailbox operations

#### Scenario: README catalog distinguishes mailbox administration from mailbox participation
- **WHEN** a reader compares the README rows for `houmao-mailbox-mgr`, `houmao-agent-email-comms`, and `houmao-process-emails-via-gateway`
- **THEN** the README explains that `houmao-mailbox-mgr` owns mailbox administration
- **AND THEN** it keeps ordinary mailbox operations and notifier-driven unread-mail rounds on the existing mailbox worker skills
