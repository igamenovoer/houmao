# Spec Delta

## ADDED Requirements

### Requirement: Hermes TUI recovery settles only from valid durable evidence
A durable Hermes TUI receipt SHALL settle an owner prompt attempt only when it satisfies the receipt contract and can be attributed to that attempt and its recorded managed authority. An incomplete, malformed, or mismatched receipt SHALL leave the attempt unresolved until valid attributable evidence settles it or authorized lifecycle recovery fences it.

#### Scenario: Incomplete terminal evidence cannot release admission
- **WHEN** owner recovery sees a receipt with a terminal outcome and matching apparent identifiers but missing required receipt fields
- **THEN** the receipt does not settle the prompt or release the unresolved owner slot
- **AND THEN** recovery does not replay the prompt

#### Scenario: Valid terminal evidence settles the matching attempt
- **WHEN** a complete durable receipt proves a terminal outcome for the exact owner attempt
- **THEN** recovery settles that attempt according to the recorded outcome

#### Scenario: A queued receipt stays queued
- **WHEN** a complete receipt proves that the native session queued the prompt
- **THEN** recovery retains the original admission and its queued status until attributable evidence changes it
