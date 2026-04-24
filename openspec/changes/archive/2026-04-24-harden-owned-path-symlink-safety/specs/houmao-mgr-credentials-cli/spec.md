## ADDED Requirements

### Requirement: Credential mutations stay within managed credential bundle roots
Credential create, set, rename, and remove flows SHALL mutate only lexical artifact paths inside the selected Houmao-managed credential bundle roots.

When credential commands consume caller-provided source files, those files SHALL be treated as read-only inputs.

#### Scenario: Clearing a symlink-backed managed credential file removes only the artifact
- **WHEN** one managed credential bundle already contains a file entry whose lexical path under the managed bundle root is a symlink
- **AND WHEN** an operator runs a credential update that clears that managed file entry
- **THEN** Houmao removes only the lexical artifact path under the managed bundle root
- **AND THEN** it does not delete or rewrite the symlink target

#### Scenario: Importing one source credential file preserves the caller-owned input
- **WHEN** an operator runs a credential update that copies one caller-provided source file into a managed credential bundle
- **THEN** the managed credential bundle is updated
- **AND THEN** the caller-provided source file remains intact
