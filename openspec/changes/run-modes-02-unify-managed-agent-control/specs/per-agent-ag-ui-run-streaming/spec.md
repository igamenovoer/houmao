# Spec Delta

## ADDED Requirements

### Requirement: Run streams preserve mode-specific correlation

An AG-UI run SHALL submit through the selected agent's shared control boundary and map events only at the correlation strength supported by that mode. Native service notifications and Web activity SHALL be bound to the selected native session and attributable turn before publication as that run's output.

#### Scenario: A browser starts another turn

- **WHEN** the native Web host reports activity for a human turn while an AG-UI run exists
- **THEN** the stream keeps that activity distinct and does not use it to complete the AG-UI run

#### Scenario: Service stream loses attribution

- **WHEN** a service reconnects without evidence binding a terminal notification to the original run
- **THEN** the stream reports a bounded error or uncertainty through its documented terminal path without fabricating a successful result or resubmitting input
