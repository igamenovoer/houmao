# Spec Delta

## ADDED Requirements

### Requirement: DSH Web qualification verifies managed Workspace navigation

Qualification SHALL use the maintained managed DSH Web fixture to verify native Workspace membership and browser selection for the published session. It SHALL collect evidence before the first prompt and observe browser entry and reload without test-only Workspace setup or session selection.

#### Scenario: A clean browser opens a fresh managed session

- **WHEN** a clean browser follows the gateway Web entry flow before any prompt
- **THEN** the native Workspace for the configured working directory lists the bound session and the browser selects it
- **AND THEN** the Workspace and session inventories are identical before entry, after entry, and after reload

#### Scenario: Explicit relaunch preserves or replaces the expected session

- **WHEN** qualification enters through the gateway after exact relaunch of a session with history and after an explicit new-session relaunch
- **THEN** exact relaunch opens the same session with its history and new-session relaunch opens one replacement in the same Workspace
- **AND THEN** previously existing sessions and unrelated Workspace records are preserved

#### Scenario: A notifier turn follows the manifest binding

- **WHEN** an operator selects an unrelated native session and the gateway mail notifier dispatches a turn
- **THEN** the fixture observes that turn in the manifest-bound native conversation after reopening the managed entry
- **AND THEN** the unrelated conversation and the managed binding retain their original identities
