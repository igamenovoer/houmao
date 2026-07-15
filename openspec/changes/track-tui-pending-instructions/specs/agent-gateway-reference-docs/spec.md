## ADDED Requirements

### Requirement: Gateway reference explains pending-input state and prompt admission decisions

The gateway contract and operations reference SHALL distinguish provider-native pending input from composer drafts, gateway-durable request queue entries, and Houmao prompt-submission notes.

The reference SHALL document `surface.pending_input`, the `ready_only | if_no_pending | always` decision table, conservative unknown handling, structural gateway checks that no policy bypasses, TUI-only non-default policies, and the removal of binary force behavior.

The gateway internals reference SHALL explain that admission uses one latest tracked snapshot without a queue-slot reservation. It SHALL state that multiple calls can dispatch before provider repaint and that later decisions react to the next observed pending-input state.

#### Scenario: Contract page distinguishes the three queue-like concepts

- **WHEN** a reader opens the gateway prompt-control contract documentation
- **THEN** the page distinguishes provider-native pending input, gateway-durable work, and user-authored composer draft text
- **AND THEN** it does not describe any one of them as authoritative for the others

#### Scenario: Operations page presents the admission decision table

- **WHEN** an operator needs to choose a direct prompt admission policy
- **THEN** the gateway operations reference shows when each policy dispatches or refuses for ready, busy-no-pending, busy-pending, and unknown observations
- **AND THEN** it explains which availability and compatibility failures remain enforceable

#### Scenario: Internals page rejects an atomic-reservation interpretation

- **WHEN** a maintainer studies closely spaced if-no-pending submissions
- **THEN** the gateway internals reference explains observation-to-repaint behavior and the absence of a pending-slot reservation
- **AND THEN** it identifies the provider TUI observation as the authority for later decisions
