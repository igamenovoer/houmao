# Spec Delta

## ADDED Requirements

### Requirement: Gateway reference documents the operator dashboard

The gateway reference SHALL show how to find the live gateway address and open its dashboard at the base URL. It SHALL explain the displayed summary, when the Web action appears, and how to reach an owner-local gateway from another execution context.

#### Scenario: An operator looks for a live Web agent

- **WHEN** a reader follows the dashboard instructions
- **THEN** the reference gives an owner-local URL example and explains immediate entry with an empty roster and sign-in with enrolled keys

#### Scenario: An operator opens the dashboard through the advertised address

- **WHEN** a reader needs Web entry from an advertised proxy deployment
- **THEN** the reference explains the owner-local connection or private TCP forwards needed for browser entry
