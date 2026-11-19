# Spec Delta

## ADDED Requirements

### Requirement: Project launch selects the native run mode before takeover

Project birth SHALL accept a single `--mode` selector, resolve the selected source and its defaults in the admitted execution context, and validate the tool, mode, and backend-specific options before force takeover, home creation, or live publication.

#### Scenario: An unsupported override targets a predecessor

- **WHEN** an operator requests DSH tui with force replacement of an existing managed agent
- **THEN** the request identifies the unsupported pair and leaves the predecessor running

#### Scenario: A delegated launch supplies an explicit mode

- **WHEN** an operator launches a profile through a named executor with an explicit supported mode
- **THEN** owner-side resolution applies the mode and returns the same tool/mode/backend binding that it persists
