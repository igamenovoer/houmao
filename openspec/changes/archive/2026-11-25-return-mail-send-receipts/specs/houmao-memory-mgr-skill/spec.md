# Spec Delta

## ADDED Requirements

### Requirement: Memory guidance separates memo write confirmation from reading

The packaged memory skill SHALL use the receipt to confirm one memo write and direct subsequent content inspection through `memo show` on the same scope.

#### Scenario: The caller wants to verify appended text

- **WHEN** a managed agent needs the resulting text after a successful memo append
- **THEN** the skill directs it to `memory memo show` in the same agent scope
- **AND THEN** it uses the append receipt for write confirmation
