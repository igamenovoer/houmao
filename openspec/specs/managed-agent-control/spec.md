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
