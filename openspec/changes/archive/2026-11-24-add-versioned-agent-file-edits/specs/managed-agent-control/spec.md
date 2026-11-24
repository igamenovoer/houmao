# Spec Delta

## ADDED Requirements

### Requirement: File Publication Uses Shared Owner Maintenance

Before changing live files, an authorized push SHALL reserve maintenance for the exact active owner generation and obtain immediate native admission for all affected execution. Manager-direct, gateway, and lifecycle operations SHALL honor the owner reservation across processes. Houmao SHALL refuse conflicting work before effects.

#### Scenario: An ordinary prompt wins owner admission

- **WHEN** a manager-direct or gateway prompt has unresolved work for the target when push requests maintenance
- **THEN** push returns busy before changing the published revision or dispatching activation

#### Scenario: Publication wins owner admission

- **WHEN** a push holds maintenance and a manager-direct or gateway prompt requests admission
- **THEN** the owner refuses the conflicting prompt before native handoff or queued acceptance

#### Scenario: A native turn or shared child prevents maintenance

- **WHEN** browser input or another execution sharing the affected resources prevents immediate native admission
- **THEN** push reports busy or unsupported before changing live files
- **AND THEN** existing native work continues under its own admission

#### Scenario: Lifecycle replacement races publication

- **WHEN** reset or relaunch would replace the execution captured by a push
- **THEN** its lifecycle operation honors the publication reservation or explicitly fences the in-flight operation before recovery
- **AND THEN** the earlier push cannot publish or activate in the replacement execution

#### Scenario: Policy revocation races the publication handoff

- **WHEN** maintenance is held and the owner revokes the exact admitted authority before the push records its shared policy handoff
- **THEN** the push refuses publication and leaves the candidate available

### Requirement: Publication Maintenance Survives Lost Callers

The owner SHALL retain an admitted maintenance reservation across caller loss, gateway detach, and gateway restart. It SHALL reopen ordinary admission only after confirming settlement and safe native readiness, or after authorized lifecycle recovery fences the affected execution. Reconciliation SHALL use attributable evidence and SHALL NOT replay the admitted publication or activation.

#### Scenario: A gateway detaches after native handoff

- **WHEN** the gateway stops serving while the admitted operation can still affect the target
- **THEN** manager-direct admission and any reattached gateway honor the reservation
- **AND THEN** the retained receipt reports uncertainty until the owner can attribute settlement evidence

#### Scenario: A completion arrives after lifecycle recovery

- **WHEN** a fenced operation reports completion after a replacement execution obtains its own reservation
- **THEN** the completion may settle only the earlier operation's receipt
- **AND THEN** the replacement's reservation and admission state remain authoritative

#### Scenario: Recovery finds an authorization handoff with unresolved publication

- **WHEN** an authorized policy handoff exists and the mount journal cannot yet establish its publication or native settlement
- **THEN** the owner retains the maintenance reservation until attributable evidence resolves the outcome or authorized recovery fences the old execution
- **AND THEN** reconciliation does not redispatch publication or activation
