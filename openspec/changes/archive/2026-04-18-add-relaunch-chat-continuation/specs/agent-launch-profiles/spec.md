## ADDED Requirements

### Requirement: Launch profiles may store relaunch chat-session policy
The shared launch-profile object family SHALL support an optional relaunch-only chat-session policy for future live managed-agent instances created from that profile.

The relaunch chat-session policy SHALL live under a relaunch-specific namespace and SHALL NOT affect first launch.

The policy SHALL support modes `new`, `tool_last_or_new`, and `exact`.

When the stored policy mode is `exact`, the profile SHALL store a non-empty provider-native session id.

When no relaunch chat-session policy is stored, instances launched from the profile SHALL use the system default relaunch chat-session mode `new`.

Profile inspection SHALL report the stored relaunch chat-session policy when present without exposing any credential material.

Patch mutation SHALL preserve an existing relaunch chat-session policy when no relaunch chat-session field is supplied. Replacement mutation SHALL clear an existing relaunch chat-session policy unless the replacement request supplies one.

#### Scenario: Profile stores latest-chat relaunch policy without changing first launch
- **WHEN** an operator creates launch profile `reviewer` with relaunch chat-session mode `tool_last_or_new`
- **AND WHEN** the operator launches a managed agent from `reviewer`
- **THEN** the first launch starts normally rather than resuming provider history
- **AND THEN** later relaunch of that managed agent uses the stored latest-chat relaunch policy unless a stronger relaunch command override is supplied

#### Scenario: Profile stores exact relaunch policy
- **WHEN** an operator creates launch profile `reviewer` with relaunch chat-session mode `exact` and provider session id `abc123`
- **THEN** the stored profile records the exact relaunch chat-session policy
- **AND THEN** inspection reports that exact provider session id as non-secret relaunch configuration

#### Scenario: Replacement clears omitted relaunch chat-session policy
- **WHEN** launch profile `reviewer` stores relaunch chat-session mode `tool_last_or_new`
- **AND WHEN** an operator replaces `reviewer` without supplying a relaunch chat-session policy
- **THEN** the replacement profile no longer records the prior relaunch chat-session policy

#### Scenario: Patch preserves omitted relaunch chat-session policy
- **WHEN** launch profile `reviewer` stores relaunch chat-session mode `tool_last_or_new`
- **AND WHEN** an operator patches only the profile workdir
- **THEN** the stored relaunch chat-session policy remains associated with the profile
