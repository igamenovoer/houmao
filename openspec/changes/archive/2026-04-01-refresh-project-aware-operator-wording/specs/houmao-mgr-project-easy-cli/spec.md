## ADDED Requirements

### Requirement: Project easy inspection and stop wording follows the selected-overlay contract
Maintained `houmao-mgr project easy ...` help text, failures, and ownership-mismatch errors SHALL use the same selected-overlay and non-creating terminology as the broader project-aware contract.

Inspection, removal, and stop commands that resolve without creating an overlay SHALL say so explicitly when no project overlay is available for the current invocation.

Ownership-mismatch failures for project-easy runtime instances SHALL describe the selected project overlay rather than a generically discovered overlay.

#### Scenario: Specialist or instance inspection failure remains explicitly non-creating
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist list` or `houmao-mgr project easy instance list`
- **THEN** the failure identifies the selected or would-bootstrap overlay root for that invocation
- **AND THEN** it states that the command did not create that overlay because the surface is non-creating

#### Scenario: Instance ownership mismatch names the selected project overlay
- **WHEN** an operator runs a maintained `houmao-mgr project easy instance get` or `stop` command
- **AND WHEN** the resolved managed-agent manifest belongs to a different overlay
- **THEN** the failure states that the managed agent does not belong to the selected project overlay
- **AND THEN** it does not describe that mismatch as a problem with a generically discovered overlay
