## ADDED Requirements

### Requirement: System-skills reference documents portable release metadata
The CLI reference SHALL explain that each of the six standalone public `SKILL.md` roots declares `houmao_version` equal to its Houmao release. It SHALL explain that shared children inherit the shared root version and do not declare independent values.

The reference SHALL distinguish installed frontmatter version, receipt package version, and content digest evidence.

#### Scenario: Reader inspects shared routines
- **WHEN** a reader asks how the sixteen shared children are versioned
- **THEN** the reference identifies `houmao-shared-routines/SKILL.md` as their version authority
- **AND THEN** it does not advertise per-child release versions

### Requirement: System-skills reference documents doctor usage
The CLI reference SHALL document doctor with explicit tool-home examples, managed-agent id and name examples, repeatable pack selection, agent-pack default, plain output, structured output, and exit codes.

It SHALL explain that doctor can inspect receiptless copy or Skills CLI installations and that managed-agent name resolution must be unique.

#### Scenario: Reader checks one managed agent
- **WHEN** a reader wants to diagnose one known managed agent
- **THEN** the reference shows the authoritative agent-id form
- **AND THEN** it explains how doctor resolves the persistent home

#### Scenario: Reader checks an external copy
- **WHEN** a reader installed the static agent roots without `houmao-mgr`
- **THEN** the reference shows explicit `--tool`, `--home`, and `--pack agent`
- **AND THEN** it states that a missing receipt does not prevent version diagnosis

### Requirement: Documentation preserves the diagnostic boundary
The reference SHALL state that `houmao_version` equality is checked only by doctor. It SHALL NOT claim that install, status, upgrade, managed launch, join, runtime authorization, or skill invocation rejects mismatched versions.

Doctor documentation SHALL describe it as read only and SHALL direct repairs to explicit install or upgrade commands rather than implying automatic mutation.

#### Scenario: Doctor reports an old release
- **WHEN** a reader receives a version mismatch
- **THEN** the reference explains that the result is diagnostic
- **AND THEN** it offers an explicit upgrade or reinstall as a separate operator decision
