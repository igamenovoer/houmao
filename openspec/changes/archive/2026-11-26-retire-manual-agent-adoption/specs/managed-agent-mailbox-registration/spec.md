## ADDED Requirements

### Requirement: Scoped offline membership commands support already managed local agent bodies
The scoped `agents single` and `agents self` command trees SHALL expose `mailbox offline status`, `join`, and `leave`. They SHALL resolve the stable agent owner and selected local or remote registry without requiring body restart. Remote body management SHALL remain outside communication-only registration authority.

#### Scenario: Offline-disabled body joins a remote registry
- **WHEN** an authorized operator selects an existing local body and joins a remote registry
- **THEN** its offline binding references the confirmed registry registration
- **AND THEN** the body process, conversation, stable agent ID, and online binding remain unchanged

#### Scenario: A running managed body joins without relaunch
- **WHEN** an agent started through a supported Houmao launch joins an offline mailbox registry while its native runtime is running
- **THEN** offline operations become actionable without relaunch or mailbox-specific environment updates

## REMOVED Requirements

### Requirement: Scoped offline membership commands support existing local agent bodies

**Reason:** Manual session adoption is retired. Offline mailbox membership remains available for a verified managed runtime.

**Migration:** Use the existing scoped `mailbox offline` commands against a running supported managed agent.
