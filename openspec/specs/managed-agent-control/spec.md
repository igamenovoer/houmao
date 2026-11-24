# managed-agent-control Specification

## Purpose

Define the control, communication, and lifecycle contract that operators and authenticated gateway clients use for every managed run mode.

## Requirements

### Requirement: Operator and gateway operations share one owner

Houmao SHALL resolve the selected agent, execution context, and current owner generation before acting. Manager lifecycle commands SHALL reach that owner even when its gateway is detached. The authenticated per-agent gateway and manager communication commands SHALL use the same owner-side admission, dispatch, and interruption rules.

#### Scenario: Gateway detaches during a turn

- **WHEN** an authenticated gateway stops serving while the agent continues a turn
- **THEN** the manager can inspect and stop the recorded owner through its saved route
- **AND** reattaching a gateway cannot create a second worker or replay a prompt

#### Scenario: Two callers target one agent

- **WHEN** a manager prompt and a ready-only gateway prompt compete for the same active slot
- **THEN** the owner admits at most one and gives the other a truthful admission result

### Requirement: Operations publish their evidence and support

The managed control contract SHALL report the resolved mode, available operations, readiness, active work, and the source and freshness of each observation. It SHALL distinguish queue acceptance, native handoff, provider completion, and uncertainty. Every adapter SHALL explicitly report unsupported operations and the strongest correlation it can actually establish.

#### Scenario: Provider cannot confirm completion

- **WHEN** a TUI accepts keystrokes but supplies no turn-correlated native completion
- **THEN** the receipt reports its observed handoff or surface evidence and leaves native completion unconfirmed

#### Scenario: Native control disappears

- **WHEN** a supervisor remains alive after its service connection is lost
- **THEN** control reports unavailability or uncertainty and refuses new work whose ownership is unresolved

#### Scenario: An operation is unavailable

- **WHEN** a caller requests a mode-specific operation that the active adapter does not support
- **THEN** the response identifies the unsupported operation before provider mutation

### Requirement: Discovery and integrations use the same control boundary

Published handoff SHALL expose only the non-secret human surface qualified for the selected mode. Mail wakeups, plugins and AG-UI submissions SHALL obey the same operation capabilities and admission as direct gateway calls. Durable message storage SHALL retain its own delivery semantics.

#### Scenario: Mail arrives during a human turn

- **WHEN** a mailbox stores a message while the owner cannot admit a wakeup
- **THEN** storage keeps its existing result and the wakeup reports its actual admission outcome

#### Scenario: Consumer discovers a service

- **WHEN** a verified owner manages a stdio-only service
- **THEN** discovery exposes its managed control reference without exporting private IPC, native tokens, or a terminal handoff

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
