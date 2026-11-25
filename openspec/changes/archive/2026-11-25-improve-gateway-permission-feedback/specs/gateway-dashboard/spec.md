# Spec Delta

## ADDED Requirements

### Requirement: The Dashboard Displays Public Roster Mode

The public dashboard SHALL show the selected gateway's open, keyed, or unavailable roster mode using the same verified evidence as endpoint discovery. Where Web entry is eligible, the dashboard SHALL explain direct entry or sign-in using that mode. Entry SHALL continue through the existing bare Web entry path and current admission checks.

#### Scenario: A browser opens the dashboard on a Web agent

- **WHEN** the dashboard can verify the current policy for an eligible Web surface
- **THEN** it shows open mode and direct-entry guidance for an empty roster, or keyed mode and sign-in guidance for a nonempty roster
- **AND THEN** the entry action still links to the bare `/v1/web/enter` path

#### Scenario: A browser opens a dashboard without eligible Web entry

- **WHEN** the dashboard describes a non-Web agent or a request that fails the existing entry eligibility checks
- **THEN** it can show the verified public roster mode alongside its existing unavailability guidance
- **AND THEN** it offers no new entry action

#### Scenario: The gateway cannot verify the current policy

- **WHEN** current policy evidence for the dashboard target is unavailable
- **THEN** the dashboard reports the roster mode as unavailable and withholds Web entry

#### Scenario: An unsigned browser reads the page on a keyed target

- **WHEN** the dashboard returns the public mode without caller proof
- **THEN** the page omits the default permission group, enrollment records, fingerprints, signer labels, keys, and tickets
- **AND THEN** following the entry action rechecks live eligibility and policy
