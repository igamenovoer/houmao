# Spec Delta

## ADDED Requirements

### Requirement: Managed Hermes Applies the Maximum Qualified Unattended Approval Posture

At managed start and explicit relaunch, Houmao SHALL establish the maximum qualified native approval posture for the selected unattended Hermes mode and verified home. Native hard denials and authority checks SHALL remain in effect. Unsupported approval behavior SHALL fail explicitly before readiness. `as_is` SHALL preserve the selected native approval policy.

#### Scenario: Unattended TUI Runs an Approval-Gated Command Without an Operator

- **WHEN** a fresh or explicitly relaunched unattended Hermes TUI runs a tool action that normally requires recoverable command approval
- **THEN** the verified native execution applies the unattended approval policy without waiting for an operator or an attached Ink viewer
- **AND THEN** attempts covered by native hard denials still fail

#### Scenario: Unattended Headless Continues the Verified Conversation

- **WHEN** an unattended finite Hermes turn executes in a fresh or explicitly relaunched managed runtime
- **THEN** the finite client uses its qualified unattended command-approval policy and the verified exact conversation
- **AND THEN** both the first turn and an exact continuation can execute an otherwise approval-gated command without human input

#### Scenario: Unattended Service Preserves Its Native Command-Approval Posture

- **WHEN** a fresh or explicitly relaunched unattended Hermes service executes a tool action normally subject to recoverable command approval
- **THEN** the verified native execution applies the unattended approval policy without waiting for an operator
- **AND THEN** native hard denials remain in effect and other managed agents retain their own approval policies

#### Scenario: As-Is Start Uses the Selected Native Policy

- **WHEN** the selected Hermes launch requests `as_is`
- **THEN** the start or explicit relaunch uses the selected native approval policy without retaining Houmao-generated unattended settings as authored policy

#### Scenario: Observation Leaves the Live Approval Policy Intact

- **WHEN** an authorized caller observes or controls an already-live Hermes runtime without requesting explicit lifecycle start or relaunch
- **THEN** the operation leaves the managed approval posture intact

### Requirement: Hermes TUI Reports Pending Native Approval

Houmao SHALL expose a safe optional `control.approval_pending` indicator from current structured approval evidence for the exact managed Hermes TUI session and execution. A verified pending approval SHALL keep the turn active and new prompt admission closed. The indicator SHALL omit the approval payload and remain unknown when the evidence is unavailable or invalid.

#### Scenario: A Manual Approval Remains Pending With Ink Detached

- **WHEN** the verified native execution for an `as_is` managed TUI awaits recoverable tool approval
- **THEN** manager, gateway, and passive-server state report pending approval and closed prompt admission independently of the Ink attachment
- **AND THEN** the response omits the native command, description, option values, file content, and other private approval data

#### Scenario: Native Settlement Clears the Pending Indicator

- **WHEN** current native evidence confirms the approval is resolved or withdrawn
- **THEN** state reports `control.approval_pending` as false and derives readiness from the remaining native work

#### Scenario: Other Prompts and Stale Approval Evidence Are Excluded

- **WHEN** native state contains a clarification, a queued prompt, or an approval from another execution generation
- **THEN** that evidence alone does not establish a pending approval for the managed execution
- **AND THEN** an unverified session or malformed approval evidence leaves the indicator unknown

## MODIFIED Requirements

### Requirement: Hermes Service Uses Persistent ACP

Hermes service mode SHALL own a persistent `hermes acp` client and its verified Hermes daemon. The adapter SHALL negotiate the protocol and bind the exact logical session before publishing readiness. It SHALL correlate prompt settlement, reverse interactions, and cancellation to the current operation. Unattended service SHALL confirm the broadest qualified native edit mode for its bound session before publishing readiness.

#### Scenario: Two Prompts Use the Same ACP Service

- **WHEN** consecutive requests are admitted to the same healthy service
- **THEN** both use the same ACP process, daemon, and bound session
- **AND THEN** resume-time replay remains historical evidence

#### Scenario: ACP Requests an Approval

- **WHEN** the peer asks for a tool approval during a turn
- **THEN** the owner responds using the authorized native policy and an advertised option while it continues to drain protocol output
- **AND THEN** unqualified client facilities or unanswered user interactions do not silently grant access

#### Scenario: Unattended Service Establishes the Broadest Qualified Native Edit Mode

- **WHEN** an unattended service starts or explicitly relaunches and verifies its ACP session
- **THEN** the owner confirms the broadest qualified native edit mode on that session before publishing readiness
- **AND THEN** ordinary supported file edits can proceed with the full scope that Hermes permits for the selected execution identity
- **AND THEN** a peer that cannot establish that mode produces an explicit compatibility failure

#### Scenario: An Unattended Tool Permission Is Attributable

- **WHEN** an unattended ACP peer sends a supported tool-permission request for the bound session and the current uncancelled operation
- **AND WHEN** the request offers one qualifying one-time allow option with an unambiguous option identifier
- **THEN** Houmao selects that advertised one-time option while continuing to drain the active turn
- **AND THEN** the response creates no persistent grant and preserves native hard denials

#### Scenario: ACP Cannot Authorize the Reverse Interaction

- **WHEN** a reverse interaction concerns another session or a cancelled or inactive operation, lacks a qualifying permission request or option, or asks for clarification, model or provider change, or another non-tool decision
- **THEN** Houmao leaves it ungranted using the applicable refusal or cancellation response
- **AND THEN** Houmao supplies no fabricated answer or consent

#### Scenario: As-Is Service Leaves Native Approval in Effect

- **WHEN** the selected ACP launch requests `as_is`
- **THEN** the owner preserves the selected native edit mode and does not apply unattended automatic tool grants

#### Scenario: ACP Disconnects During Work

- **WHEN** the ACP process or stream disappears after a prompt may have been submitted
- **THEN** the owner reports uncertainty until it verifies the exact native outcome
- **AND THEN** viewer exit is insufficient evidence of cancellation
