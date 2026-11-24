# Houmao Agent Files Skill Delta

## ADDED Requirements

### Requirement: The Agent Files Routine Teaches Scheduled Self-Publication

The routine SHALL teach `agents self files push --when-idle` for a saved candidate on a qualified own mount. It SHALL distinguish accepted pending work from publication and native activation. It SHALL use `files status` with the original operation ID for reconciliation.

#### Scenario: Bob Finishes a Self-Update Without Another Publisher

- **WHEN** Bob saves a common-plugin candidate during his own active turn
- **THEN** the routine guides him to schedule the exact candidate and its expected base using current managed-self proof
- **AND THEN** it reports the operation ID and uses the retained receipt to establish the eventual result

#### Scenario: An Immediate Push Reports Busy

- **WHEN** Bob's immediate push returns a confirmed `busy` result
- **THEN** the routine reports the candidate as saved
- **AND THEN** a later explicit publish-at-idle request uses a fresh operation ID
