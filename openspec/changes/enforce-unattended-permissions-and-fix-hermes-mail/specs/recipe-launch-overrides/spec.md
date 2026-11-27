# Spec Delta

## MODIFIED Requirements

### Requirement: Authored tool parameters take precedence over launch defaults

Houmao SHALL apply winning authored values and resolve omissions subject to the launch policy. Under `unattended`, normalized winning permission values SHALL match the qualified posture. Under `as_is`, supported authored permissions and the native baseline for omissions SHALL apply. Supported explicit null, false, and empty inputs SHALL retain their schema-defined meanings. Native projection SHALL preserve authored inputs.

#### Scenario: An inherited explicit value replaces an unattended default

- **WHEN** an operator changes a launch from `unattended` to `as_is` to use a supported inherited sandbox value from the selected tool setup
- **AND WHEN** the specialist, profile, and one-shot inputs omit that field
- **THEN** the setup's sandbox value reaches the native agent
- **AND THEN** an omitted approval field uses the applicable native baseline

#### Scenario: An explicit false differs from omission

- **WHEN** a supported boolean parameter defaults to true and a user explicitly supplies false at a winning layer
- **THEN** the effective and projected native value is false

#### Scenario: A direct input overrides an inherited native value

- **WHEN** an `as_is` launch selects a setup with a recognized native permission value and the one-shot tool parameters supply another supported value for that field
- **THEN** the one-shot value reaches the native agent
- **AND THEN** the authored setup and stored definitions retain their values

#### Scenario: Only the normalized winning authored permission is tested against unattended posture

- **WHEN** the selected setup, stored definitions, or native argument aliases supply valid values for the same permission field
- **THEN** the applicable layer and alias precedence determines the winning value
- **AND THEN** an unattended launch accepts a missing or matching effective value and rejects a different winning value
- **AND THEN** field and reserved-control validation still applies to all selected authored inputs

#### Scenario: Effective conflict from retained launch inputs preserves the source

- **WHEN** a saved definition, recipe, or direct launch snapshot produces a conflicting effective permission under current unattended policy
- **THEN** launch rejects that field before changing existing runtime state or starting a provider and explains the `as_is` path
- **AND THEN** stored inputs remain intact for a later launch under the requested custom posture
