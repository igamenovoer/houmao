# Spec Delta

## ADDED Requirements

### Requirement: An owned DSH Web host supports gateway browser sign-in

The DSH Web backend SHALL supply the owning gateway with a private native root sign-in destination for its verified live host. The browser SHALL use the native launch-token exchange to establish its own cookie. The operator SHALL be able to select the bound native session by its published identity.

#### Scenario: A fresh browser enters through the gateway

- **WHEN** an operator redeems a valid ticket for a live DSH Web agent in a clean browser context
- **THEN** DSH establishes its native browser cookie and redirects to a clean URL
- **AND THEN** the operator can select the exact managed session and observe its conversation without opening a private bootstrap file

#### Scenario: Browser entry leaves the programmatic peer independent

- **WHEN** the browser signs in to the same host as Houmao's API peer
- **THEN** native browser authentication establishes a separate browser connection and preserves the managed API binding

#### Scenario: DSH bootstrap data does not match the live execution

- **WHEN** the credential source, native origin, or authenticated host identity fails its owner checks
- **THEN** the backend withholds the browser destination
