## ADDED Requirements

### Requirement: Managed prompt header reference documents the memo cue section
The managed prompt header reference page SHALL document the `memo-cue` managed-header section.

At minimum, the page SHALL explain:

- the policy section name `memo-cue`,
- the rendered tag `<memo_cue>`,
- that `memo-cue` defaults to enabled whenever the whole managed header is enabled,
- that `memo-cue` renders after `identity` and before `houmao-runtime-guidance`,
- that the section includes the resolved absolute path to the managed agent's fixed `houmao-memo.md`,
- that the section tells agents to read that memo file at the start of each prompt turn before planning or acting,
- that section-level policy can disable `memo-cue` without disabling the rest of the managed header.

#### Scenario: Reader sees memo cue defaults and path behavior
- **WHEN** a reader opens `docs/reference/run-phase/managed-prompt-header.md`
- **THEN** the page documents `memo-cue` as a default-enabled managed-header section
- **AND THEN** it states that the section includes the resolved absolute `houmao-memo.md` path

#### Scenario: Reader sees how to disable memo cue only
- **WHEN** a reader looks up managed-header section controls
- **THEN** the page documents that `memo-cue=disabled` suppresses the memo cue section
- **AND THEN** it distinguishes that section-level disable from whole-header `--no-managed-header`

