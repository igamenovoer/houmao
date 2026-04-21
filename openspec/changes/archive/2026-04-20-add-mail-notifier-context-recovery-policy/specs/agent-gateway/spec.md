## ADDED Requirements

### Requirement: Gateway clean-context recovery remains explicit or policy-selected
Gateway prompt control SHALL continue to treat recoverable degraded chat context as compatible with ordinary current-context prompt delivery when the target otherwise satisfies the prompt-ready contract.

Clean-context prompt delivery SHALL occur only when one of the following is true:

- the caller explicitly requests clean context through a supported prompt-control chat-session selector,
- a gateway-owned automation policy explicitly selects clean-context recovery for a recognized degraded compaction diagnostic.

For TUI-backed Codex targets, supported clean-context delivery SHALL use the tool-appropriate reset signal and wait for prompt-ready posture before sending the semantic prompt.

For native headless targets, supported clean-context delivery SHALL use the explicit fresh provider-chat selection where that backend supports it.

Recoverable degraded context, generic current-error diagnostics, or historical compact/server text SHALL NOT by themselves select clean-context delivery.

#### Scenario: Ordinary degraded prompt still uses current context
- **GIVEN** a TUI-backed gateway target is prompt-ready with recoverable degraded chat context
- **WHEN** a caller submits direct prompt control without a clean-context selector
- **THEN** the gateway sends the caller's prompt through ordinary current-context prompt delivery
- **AND THEN** it does not first clear context solely because degraded context is present

#### Scenario: Explicit selector still requests clean context
- **GIVEN** a gateway target supports clean-context prompt control
- **WHEN** a caller submits a prompt with an explicit fresh chat-session selector
- **THEN** the gateway uses the supported clean-context workflow for that target
- **AND THEN** the caller's semantic prompt is sent only after clean-context selection or reset succeeds

#### Scenario: Notifier policy can select clean context
- **GIVEN** a gateway-owned mail-notifier policy explicitly selects clean-context recovery for a recognized degraded compaction diagnostic
- **AND GIVEN** the target supports clean-context prompt delivery
- **WHEN** the notifier submits its semantic mailbox notification prompt
- **THEN** the gateway uses clean-context prompt delivery because the notifier policy selected it
- **AND THEN** the same degraded diagnostic would not have selected clean context without that policy

#### Scenario: Generic degraded evidence does not select clean context
- **GIVEN** a gateway target is prompt-ready with current-error or degraded diagnostic evidence that is not a recognized compaction diagnostic for the owning CLI tool
- **WHEN** ordinary prompt control or notifier prompt delivery occurs without an explicit clean-context selector or policy match
- **THEN** the gateway does not run a reset-then-send workflow
- **AND THEN** it does not force a native headless fresh-chat selector solely from that generic evidence
