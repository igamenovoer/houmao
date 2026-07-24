## ADDED Requirements

### Requirement: Instance contracts carry runtime-variable and mindset declarations
An Agent Definition instance contract SHALL carry immutable runtime-variable declarations, mindset declarations, and skill bindings without mutable values or records.

#### Scenario: Definition is deployed
- **WHEN** a valid revision contains instance-state declarations
- **THEN** deployment SHALL preserve their exact content and digest for later launch

### Requirement: Bound skills declare maintained state-consumption phases
Definition validation SHALL require static skills with live variable or mindset consumers to declare the maintained verified-self read phase.

#### Scenario: Static skill embeds a launch-time value
- **WHEN** a skill that requires a live variable contains a concrete rendered value instead of the maintained lookup phase
- **THEN** definition validation SHALL reject the consumer mapping
