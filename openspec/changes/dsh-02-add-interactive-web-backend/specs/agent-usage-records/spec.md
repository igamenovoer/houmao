# Spec Delta

## ADDED Requirements

### Requirement: DSH Web Accounting Includes Verified Human-Initiated Work

The bound DSH Web session SHALL use the shared native-journal accounting contract for human and managed work. Native turn identity, terminal outcome, source boundaries, and actual request route SHALL establish accounting. Browser connection state and visible output SHALL not substitute for provider evidence, and unrelated host sessions SHALL remain excluded.

#### Scenario: A Human Completes a Browser Turn
- **WHEN** a human submits work directly to the bound Web session and qualified native evidence records its requests and terminal outcome
- **THEN** a native-observed usage record appears in the existing runtime-session stream
- **AND THEN** no Houmao prompt submission is required to make that work accountable

#### Scenario: Human Changes the Model in the Browser
- **WHEN** later native requests use a model/provider route selected through the browser
- **THEN** their usage retains that actual route evidence
- **AND THEN** earlier records are not relabeled with the new model selection

### Requirement: Mixed Web Input Does Not Create Duplicate or Invented Charges

Managed Web submissions SHALL correlate through native input identity and claim evidence. A native turn containing human and managed input SHALL be accounted once with its real scope; token shares by sender SHALL not be fabricated. Human work outside a proven managed association SHALL remain independently native-observed rather than being absorbed by a broad wait-for-idle interval.

#### Scenario: Human Steering Shares a Managed Turn
- **WHEN** human steering is consumed within a native turn also associated with a managed submission
- **THEN** the turn's provider requests contribute once with mixed-input attribution
- **AND THEN** collection does not emit an additional human record covering those same requests

#### Scenario: Human Follow-Up Runs Before a Programmatic Wait Returns
- **WHEN** a human's distinct follow-up turn runs before a shared-session wait becomes idle
- **THEN** its usage follows its actual native input/turn association
- **AND THEN** wait timing alone does not charge that turn to the earlier managed submission

### Requirement: Web Observation Recovery Preserves Accounting Continuity

DSH Web API reconnection, gateway restart, and explicit host relaunch SHALL preserve existing journal bindings, accounting identities, and finalized records. Repeated API events and native journal copies SHALL contribute once. Unknown observation gaps SHALL remain explicit, and failed attempts SHALL never be executed again to reconstruct usage.

#### Scenario: API Stream Repeats Events After Reconnect
- **WHEN** a Web event is observed again after connection recovery and also exists in the bound journal
- **THEN** the same native request contributes once using its verified source identity

#### Scenario: Host Relaunch Preserves a Conversation
- **WHEN** explicit relaunch restores the same native conversation under another host incarnation
- **THEN** new observations retain the correct generation and historical baseline
- **AND THEN** prior usage is not charged again merely because the connection identity changed
