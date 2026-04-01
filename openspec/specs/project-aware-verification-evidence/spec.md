# project-aware-verification-evidence Specification

## Purpose
TBD - created by archiving change verify-project-aware-operations. Update Purpose after archive.
## Requirements
### Requirement: Project-aware contract has automated verification coverage
The repository SHALL include automated verification for the maintained project-aware contract across overlay selection, non-creating resolution, overlay-local placement, cleanup override behavior, and maintained server-start behavior.

#### Scenario: Overlay selection and boundary handling are covered
- **WHEN** maintainers run the automated verification added for this change
- **THEN** it MUST cover overlay-selection precedence, nearest-ancestor overlay reuse, and `.git` file-or-directory worktree boundary handling for nested repositories

#### Scenario: Non-creating and bootstrap behavior are covered
- **WHEN** maintainers run the automated verification added for this change
- **THEN** it MUST cover `houmao-mgr project status` remaining non-creating and commands that implicitly bootstrap the selected overlay reporting that bootstrap explicitly in text or structured payloads

#### Scenario: Overlay-local roots and explicit overrides are covered
- **WHEN** maintainers run the automated verification added for this change
- **THEN** it MUST cover overlay-local runtime or jobs or mailbox placement for maintained build, launch, mailbox, cleanup, and server paths, plus explicit shared-root override behavior where the contract still allows it

### Requirement: Verification stays anchored to maintained command surfaces
Automated verification added by this change SHALL target maintained `houmao-mgr`, `houmao-server`, `houmao-passive-server`, and maintained demo surfaces instead of deprecated compatibility entrypoints.

#### Scenario: Maintained surfaces are the validation target
- **WHEN** verification scenarios are selected for project-aware coverage
- **THEN** the automated matrix MUST use maintained command families and maintained demo fixtures as the source of truth for the contract

