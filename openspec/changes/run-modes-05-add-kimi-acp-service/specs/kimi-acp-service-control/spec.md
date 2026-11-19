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

The adapter SHALL create sessions only for explicit new-conversation selection and SHALL bind continuation to the exact recorded Kimi session and workspace. It SHALL negotiate the appropriate resume or load operation and distinguish replayed history from new prompt output, native admission, and new accounting.

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

A Kimi prompt, session-scoped cancellation, and provider-initiated interaction SHALL use the verified service binding. The adapter SHALL preserve event identity and stop reasons, handle or decline interactions under the selected policy, and expose bounded uncertainty when it loses the native outcome.

#### Scenario: An approval arrives during a turn

- **WHEN** Kimi requests permission or another supported interaction while a gateway prompt is pending
- **THEN** the owner applies the authorized policy while updates continue and the same prompt reaches its actual outcome

#### Scenario: A stale cancel follows a second prompt

- **WHEN** the prior request has settled and a new prompt is active on the same session
- **THEN** the stale operation cannot cancel the new turn

#### Scenario: Gateway restarts between prompts

- **WHEN** the gateway reattaches to a healthy Kimi service
- **THEN** its next ordinary submission uses the same native process and session
