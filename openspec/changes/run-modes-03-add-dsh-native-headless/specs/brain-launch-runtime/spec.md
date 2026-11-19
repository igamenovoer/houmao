# Spec Delta

## ADDED Requirements

### Requirement: DSH headless selection resolves to the native CLI backend

Project launch, definitions, and headless-only server birth SHALL select `dsh_headless` for qualified DSH headless execution. The manifest SHALL bind logical agent, runtime session, generation, native session when known, and tool build. Stale readers SHALL preserve newer turn or native-session bindings.

#### Scenario: Project launches DSH headless

- **WHEN** a valid project profile selects `dsh` and `headless`
- **THEN** the manager publishes normal discovery metadata for the `dsh_headless` managed turn envelope

#### Scenario: A stale controller inspects completed work

- **WHEN** another controller has saved a newer native session or turn binding
- **THEN** capability, status, attach, and detach preserve the newer state

## MODIFIED Requirements

### Requirement: DSH Headless Lifecycle Uses the Managed Turn Envelope

DSH headless turns SHALL use the maintained tmux-backed managed turn envelope, canonical semantic events, durable terminal evidence, and exact native continuation. Stop, interrupt, relaunch, reset, gateway attachment, and usage recovery SHALL retain their established identity boundaries. Starting an explicitly new conversation SHALL create a new source binding without discarding runtime-session history.

#### Scenario: A Headless Turn Exits Between Prompts
- **WHEN** a DSH turn completes and its one-shot CLI worker exits while the managed tmux session remains live
- **THEN** the logical agent remains discoverable and gateway-attachable
- **AND THEN** a later explicit prompt can resume the saved native conversation

#### Scenario: An Operator Resets the Native Conversation
- **WHEN** the operator explicitly selects a new DSH conversation within an existing runtime session
- **THEN** the next turn uses a new native identity and source binding
- **AND THEN** earlier usage and terminal results remain attributed to their original conversation and generation

#### Scenario: An Attempt Dies After Admission
- **WHEN** an admitted DSH attempt loses its owned process or execution generation
- **THEN** its response or recorded outcome reports failure or uncertainty
- **AND THEN** relaunch does not automatically resend that attempt's prompt

## REMOVED Requirements

### Requirement: DSH Headless Selection Resolves to Its ACP Backend

**Reason**: DSH headless now selects its native one-shot executable profile.

**Migration**: Use `--mode headless` for the native CLI and `--mode service` for ACP once qualified.
