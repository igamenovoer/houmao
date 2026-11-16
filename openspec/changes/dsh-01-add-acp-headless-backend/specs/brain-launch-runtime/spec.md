# Spec Delta

## ADDED Requirements

### Requirement: DSH Headless Selection Resolves to Its ACP Backend

An explicitly headless DSH launch SHALL resolve to backend `dsh_acp` through maintained definitions, profiles, and manager paths. Runtime manifests SHALL preserve the logical agent, runtime session, generation, native session, and qualified tool-build identities. Unsupported mode or backend combinations SHALL fail before provider launch.

#### Scenario: Project Launch Selects DSH Headless
- **WHEN** a valid project launch profile selects tool `dsh` and headless posture
- **THEN** launch selects `dsh_acp` and publishes ordinary managed-agent identity and discovery state
- **AND THEN** the launch does not require a separate custom launcher

#### Scenario: Stale Controller Inspects a Completed Native Turn
- **WHEN** another controller has persisted a newer DSH native session or turn binding
- **THEN** later capability, status, attach, or detach operations preserve that newer persisted state

### Requirement: DSH Runtime Configuration Is Explicit and Isolated

Managed DSH launches SHALL isolate the Harness home, shared-agent root, profile, persistence, and selected skill roots. Provider route, endpoint protocol, credential reference, model, and required model metadata SHALL resolve explicitly. Native DeepSeek Messages and generic compatible routes SHALL remain distinct configurations, and secrets SHALL stay outside persisted public launch metadata.

#### Scenario: Two Agents Use Different Model Routes
- **WHEN** two DSH agents use different credentials, models, skill sets, or endpoints in the same workspace
- **THEN** each agent uses its selected managed configuration without inheriting the other's home, history, or user-global credentials

#### Scenario: A Chat Endpoint Is Supplied to a Messages Route
- **WHEN** a selected DSH route requires Messages but the supplied endpoint configuration declares only Chat Completions
- **THEN** validation rejects the combination before agent work
- **AND THEN** Houmao does not relabel the protocol or silently choose another model adapter

#### Scenario: The Provider Route Is Missing
- **WHEN** a managed DSH setup has no valid selected provider route or lacks required model metadata
- **THEN** launch fails with an actionable missing-input diagnostic instead of using a shipped model or capacity default

### Requirement: DSH Roles Are Applied as Literal Native System Instructions

Before DSH processes the first user prompt, the complete effective Houmao launch prompt SHALL be installed through a native system-prompt section that preserves literal text and DSH's required tool guidance. Projection SHALL record non-secret provenance. Empty prompts SHALL remove stale managed role content, and failure SHALL NOT fall back to a skill or chat bootstrap.

#### Scenario: Role Contains Template-Like Text
- **WHEN** an effective role contains `{{example}}`, dollar expressions, quotes, or multiline code
- **THEN** DSH receives those bytes literally in native system instructions
- **AND THEN** the role is not submitted as an ordinary user message

#### Scenario: An Empty Role Replaces an Earlier Role
- **WHEN** a preserved DSH home is rebuilt with an empty effective launch prompt
- **THEN** stale Houmao-owned role content is absent before provider execution

### Requirement: DSH Headless Lifecycle Uses the Managed Turn Envelope

DSH headless turns SHALL use the maintained tmux-backed managed turn envelope, canonical semantic events, durable terminal evidence, and exact native continuation. Stop, interrupt, relaunch, reset, gateway attachment, and usage recovery SHALL retain their established identity boundaries. Starting an explicitly new conversation SHALL create a new source binding without discarding runtime-session history.

#### Scenario: A Headless Turn Exits Between Prompts
- **WHEN** a DSH turn completes and its ACP worker exits while the managed tmux session remains live
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
