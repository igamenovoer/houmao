## ADDED Requirements

### Requirement: README system-skills subsection lists the touring skill
The `README.md` system-skills subsection SHALL list `houmao-touring` as one of the current packaged Houmao-owned system skills.

That catalog row or list entry SHALL describe `houmao-touring` as the manual guided-tour skill for first-time or re-orienting users.

The README SHALL explain that `houmao-touring` is a branching guided entrypoint that can orient the user across project setup, mailbox setup, specialist or profile authoring, live-agent operations, and lifecycle follow-up.

The README SHALL state that `houmao-touring` is manual-invocation-only rather than the default entrypoint for ordinary direct-operation requests.

#### Scenario: Reader sees the touring skill in the README catalog
- **WHEN** a reader scans the README system-skills catalog table or list
- **THEN** they find `houmao-touring` with a one-line description
- **AND THEN** the description presents it as a guided tour skill rather than as a direct-operation manager

#### Scenario: README describes touring as manual-only and branching
- **WHEN** a reader checks the `houmao-touring` entry in the README system-skills subsection
- **THEN** the README states that the skill is manual-invocation-only
- **AND THEN** it explains that the touring flow can branch across setup, launch, live operations, and lifecycle follow-up
