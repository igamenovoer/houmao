## ADDED Requirements

### Requirement: The packaged authoring route maintains workspace orientation

The packaged `houmao-shared-routines->houmao-agent-definition` skill SHALL tell an admin authoring an Agent Definition to create and refresh `<authoring-dir>/README.md` according to the Agent Definition authoring README contract. The route SHALL keep README maintenance inside `definition-authoring` and SHALL preserve initialization, derivation, approval, preview, materialization, and validation as separate phases.

#### Scenario: Manual authoring stops before approval

- **WHEN** an admin explicitly asks the route to initialize and derive an authoring workspace but stop before approval
- **THEN** the route creates or refreshes the root README after derivation
- **AND THEN** it still stops before approval, preview, and immutable revision write

#### Scenario: Natural-language authoring activates the admin route

- **WHEN** a human operator naturally asks to turn an existing overview into a reusable Houmao Agent Definition
- **THEN** the admin entrypoint routes to `definition-authoring`
- **AND THEN** the authoring route refreshes the root README before returning derivation findings

#### Scenario: README does not replace maintained commands

- **WHEN** the authoring route generates or refreshes workspace orientation
- **THEN** it continues using maintained `houmao-mgr` commands for initialization, derivation, approval, materialization, and validation
- **AND THEN** it does not claim that README generation is a `houmao-mgr` subcommand
