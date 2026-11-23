# Spec Delta

## ADDED Requirements

### Requirement: Managed DSH Web lifecycle verifies native Workspace membership

Houmao SHALL register or reuse the native Workspace for the canonical launch working directory. It SHALL verify that the Workspace includes the exact managed native session before publishing a ready DSH Web binding.

#### Scenario: A fresh session is available before its first turn

- **WHEN** Houmao launches DSH Web in a working directory with no native Workspace
- **THEN** one Workspace exists at that directory and its membership includes the manifest-bound native session before any prompt is submitted

#### Scenario: Exact relaunch retains the native session

- **WHEN** the operator explicitly relaunches DSH Web with the recorded exact session ID
- **THEN** the new execution publishes the same native session ID and verifies its membership in the same Workspace
- **AND THEN** repeated setup leaves one Workspace registration and one membership for that session

#### Scenario: An explicit replacement joins the managed Workspace

- **WHEN** the operator requests a new conversation through relaunch or an in-place reset
- **THEN** Houmao binds one replacement session in the same Workspace
- **AND THEN** prior and unrelated Workspace records, sessions, and histories are preserved

#### Scenario: Workspace setup fails

- **WHEN** the workdir or native membership cannot be verified during a managed lifecycle operation
- **THEN** Houmao reports a bounded, secret-redacted lifecycle error and withholds the ready binding for that execution

## MODIFIED Requirements

### Requirement: An owned DSH Web host supports gateway browser sign-in

The DSH Web backend SHALL supply the owning gateway with a private native sign-in destination for its verified live host and managed session. The browser SHALL use DSH's native launch-token exchange to establish a separate cookie and open the managed session in its Workspace.

#### Scenario: A fresh browser enters through the gateway

- **WHEN** an operator redeems a valid ticket for a live DSH Web agent in a clean browser context
- **THEN** DSH establishes its native browser cookie and lands on a clean URL with the manifest-bound session selected in its Workspace
- **AND THEN** entry leaves the Workspace and session inventories unchanged, including when the target is blank

#### Scenario: Browser entry leaves the programmatic peer independent

- **WHEN** the browser signs in to the same host as Houmao's API peer
- **THEN** native browser authentication establishes a separate browser connection and preserves the managed API binding

#### Scenario: DSH bootstrap data does not match the live execution

- **WHEN** the credential source, native origin, authenticated host identity, or managed session membership fails its owner checks
- **THEN** the backend withholds the browser destination

#### Scenario: A fresh browser enters from an open gateway

- **WHEN** a clean browser opens the bare entry URL for a verified live DSH Web agent with a valid empty roster
- **THEN** the gateway immediately redirects to DSH's native browser sign-in destination
- **AND THEN** DSH establishes the browser's cookie and selects the managed session directly with the existing Workspace and session inventories

#### Scenario: A browser re-enters after navigating elsewhere

- **WHEN** an operator opens the gateway entry flow with a different native session saved in the browser
- **THEN** the new handoff selects the current managed session
- **AND THEN** subsequent native navigation and reload follow the browser's selection while Houmao prompts and mail notifications keep using the manifest-bound session
