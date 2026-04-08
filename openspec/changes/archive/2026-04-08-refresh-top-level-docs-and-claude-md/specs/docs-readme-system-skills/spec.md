## ADDED Requirements

### Requirement: README does not contain a Current Status stability paragraph

The `README.md` file SHALL NOT contain a "Current Status" section (or any equivalently titled leading paragraph) that frames the `houmao-mgr` plus `houmao-server` operator surface as unstable, actively churning, or still stabilizing.

The opening content above the "Project Introduction" section SHALL jump directly from the project tagline to the introductory material without a separate status-disclaimer paragraph.

#### Scenario: Reader opens README without a misleading stability warning

- **WHEN** a reader opens `README.md` and reads from the top
- **THEN** there is no "Current Status" heading or section
- **AND THEN** there is no leading paragraph that tells the reader the operator interface is unstable or still stabilizing

#### Scenario: README does not describe `houmao-mgr` plus `houmao-server` as stabilizing

- **WHEN** searching `README.md` content above the "Project Introduction" section
- **THEN** the text does not claim that the operator interface is stabilizing, unstable, or likely to change
