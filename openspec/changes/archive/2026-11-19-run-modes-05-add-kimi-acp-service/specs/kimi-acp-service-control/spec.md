# Spec Delta

## Purpose

Specify the qualified Kimi Code ACP adapter for Houmao service mode, including native session identity, protocol capabilities, and attributable turn evidence.

## ADDED Requirements

### Requirement: Kimi service negotiates its own ACP capabilities

Kimi service mode SHALL start `kimi acp` over owner-private stdio with the selected execution home, workspace, environment, and operator policy. The adapter SHALL initialize and record Kimi's actual protocol capabilities. It SHALL declare only client capabilities implemented within that owner's authority.

#### Scenario: A maintained Kimi ACP build starts

- **WHEN** native initialization and session binding both succeed
- **THEN** the service becomes ready with the actual Kimi capabilities and no terminal or Web handoff

#### Scenario: A requested capability is unavailable

- **WHEN** the selected Kimi build lacks a required session operation or asks for an unsupported client facility
- **THEN** the adapter reports the limitation without invoking a different mode or granting undeclared access

### Requirement: Kimi continuation and history preserve exact identity

The adapter SHALL create sessions only for explicit new-conversation selection and SHALL verify the recorded Kimi session in the private home and workspace before requesting continuation. It SHALL negotiate the appropriate resume or load operation and distinguish replayed history from new prompt output, native admission, and accounting. The ACP binding response and a session listing alone SHALL NOT establish workspace identity.

#### Scenario: Resume succeeds after service relaunch

- **WHEN** the saved Kimi session exists in the selected home and workspace
- **THEN** the new incarnation binds that session and the next request continues its conversation

#### Scenario: Load replays history

- **WHEN** a qualified load method emits messages before any new prompt is admitted
- **THEN** those messages are classified as historical and cannot settle a new request or create duplicate usage

#### Scenario: A saved session is missing

- **WHEN** a launch requests continuation for an inaccessible session
- **THEN** the adapter reports failure without selecting a recent session or creating a replacement

### Requirement: Kimi service uses shared admission and native settlement

Kimi input, cancellation and interactions SHALL use the verified service binding. The owner SHALL recheck admission immediately before input and persist the write attempt. The adapter SHALL preserve event identity and stop reasons, apply the selected interaction policy, and expose uncertainty when it loses the native outcome. Ordinary success SHALL require a correlated reply and matching new native journal evidence.

#### Scenario: An approval arrives during a turn

- **WHEN** Kimi requests permission or another supported interaction while a gateway prompt is pending
- **THEN** the owner applies the authorized policy while updates continue and the same prompt reaches its actual outcome

#### Scenario: A stale cancel follows a second prompt

- **WHEN** the prior request has settled and a new prompt is active on the same session
- **THEN** the stale operation cannot cancel the new turn

#### Scenario: The correlated reply has no native turn

- **WHEN** an ordinary prompt receives `end_turn` and the new native journal cannot prove a matching turn
- **THEN** the owner preserves the attempted handoff and reports failure or uncertainty without repeating the prompt

#### Scenario: Gateway restarts between prompts

- **WHEN** the gateway reattaches to a healthy Kimi service
- **THEN** its next ordinary submission uses the same native process and session

### Requirement: Kimi service accounts for attributable native usage

The adapter SHALL derive managed per-turn usage from the exact native journal interval. Replay and session-scoped context occupancy SHALL NOT enter the per-turn usage ledger.

#### Scenario: Context occupancy arrives after settlement

- **WHEN** Kimi emits a delayed ACP usage update with session context totals
- **THEN** it cannot alter the original request's accounting or create usage for a newer request
