# Spec Delta

## Purpose

Define Houmao's managed Codex app-server adapter, including protocol negotiation, exact thread continuity, and correlated turn control and lifecycle.

## ADDED Requirements

### Requirement: Codex service completes the native handshake

The app-server adapter SHALL start an owner-private Codex app-server in the selected execution context, complete `initialize` and `initialized`, and verify its qualified protocol contract before reporting ready. A managed agent SHALL own its provider instance and logical thread.

#### Scenario: The peer fails initialization

- **WHEN** a Codex build rejects the handshake or lacks the qualified protocol shape
- **THEN** launch reports the incompatible service and cleans up owned resources without submitting application traffic

#### Scenario: Another app-server is already running

- **WHEN** an unrelated daemon or listener exists in the selected environment
- **THEN** a new managed launch cannot bind to it as the agent's authority

### Requirement: Codex thread and turn control follow the qualified wire contract

The adapter SHALL create or exactly resume a thread using `thread/start` or `thread/resume`. It SHALL submit `turn/start` with a `threadId` and typed input array, bind the returned turn ID, and correlate notifications and terminal outcomes to that thread and turn. Native interruption SHALL target the verified active thread and turn.

#### Scenario: A turn returns a handle before completion

- **WHEN** the app-server acknowledges `turn/start` and subsequently emits item and completion notifications
- **THEN** the managed receipt distinguishes the handle from settlement and reports completion only from evidence for that thread and turn

#### Scenario: An interrupt or notification references foreign work

- **WHEN** the thread, turn, service incarnation, or managed generation differs
- **THEN** it cannot operate on or complete the current managed request

#### Scenario: An exact thread cannot resume

- **WHEN** a continued launch cannot bind the requested thread in its saved home and workspace
- **THEN** the launch fails without a new thread or prompt replay

### Requirement: Provider requests and uncertain outcomes are bounded

Codex server-initiated requests SHALL be handled according to the selected approval policy and qualified methods. Unsupported requests SHALL receive a bounded response. A lost connection after admission SHALL leave the original turn uncertain until verified evidence reconciles it.

#### Scenario: The server asks for approval

- **WHEN** a supported approval request arrives during a managed turn
- **THEN** the owner answers according to policy and continues draining that turn's notifications

#### Scenario: The connection breaks after dispatch

- **WHEN** the owner cannot tell whether Codex admitted or completed a turn
- **THEN** recovery reports the available evidence without starting or sending another turn
