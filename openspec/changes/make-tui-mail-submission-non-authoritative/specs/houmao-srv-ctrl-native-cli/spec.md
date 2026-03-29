## MODIFIED Requirements

### Requirement: `houmao-mgr agents mail` exposes pair-native mailbox follow-up commands
`houmao-mgr` SHALL expose a native `agents mail ...` command family for mailbox follow-up on managed agents.

At minimum, that family SHALL include:

- `status`
- `check`
- `send`
- `reply`

Those commands SHALL address managed agents by managed-agent reference and SHALL dispatch mailbox work by the resolved managed-agent authority:

- pair-managed targets SHALL use pair-owned mail authority,
- local managed targets SHALL use manager-owned local mail authority when that authority can execute the mailbox operation directly,
- local managed targets MAY fall back to TUI-mediated request submission when direct manager-owned execution is not available,
- callers SHALL NOT be required to discover or call gateway endpoints directly themselves.

For local managed targets, ordinary mailbox follow-up SHALL NOT require prompting the target agent to interpret mailbox instructions when manager-owned mailbox execution is available.

When a local managed target uses TUI-mediated fallback, `houmao-mgr agents mail ...` SHALL treat the outcome as non-authoritative request lifecycle state rather than mailbox success or failure inferred from exact transcript parsing.

In that fallback mode, the command result SHALL distinguish at least:

- request submitted,
- request rejected before submission,
- busy or unavailable session,
- TUI or runtime error.

The command SHALL surface whether the result is authoritative.

#### Scenario: Operator inspects mail status through pair authority for a pair-managed target
- **WHEN** an operator runs `houmao-mgr agents mail status <agent-ref>`
- **AND WHEN** `<agent-ref>` resolves through pair authority
- **THEN** `houmao-mgr` resolves that managed agent through the supported pair authority
- **AND THEN** the command returns pair-owned mailbox status without requiring the operator to reach the gateway port directly

#### Scenario: Operator checks mail through local manager-owned authority for a local target
- **WHEN** an operator runs `houmao-mgr agents mail check <agent-ref>`
- **AND WHEN** `<agent-ref>` resolves to local managed-agent authority on the current host
- **AND WHEN** manager-owned local mail execution is available
- **THEN** `houmao-mgr` performs mailbox follow-up through manager-owned local mail authority
- **AND THEN** the command returns an authoritative mailbox result without requiring agent-prompt mediation

#### Scenario: Local TUI-mediated fallback returns submission-only state
- **WHEN** an operator runs `houmao-mgr agents mail send <agent-ref> ...`
- **AND WHEN** `<agent-ref>` resolves to local managed-agent authority on the current host
- **AND WHEN** the only available execution path is TUI-mediated prompt submission into the live session
- **THEN** the command returns non-authoritative request lifecycle state rather than inferred mailbox success from exact TUI transcript parsing
- **AND THEN** the result tells the operator that mailbox verification must use manager-owned follow-up or protocol-owned state

#### Scenario: Mail command fails clearly when no supported mailbox follow-up authority is available
- **WHEN** an operator runs `houmao-mgr agents mail send <agent-ref> ...`
- **AND WHEN** the addressed managed agent exposes neither actionable pair-owned nor actionable local manager-owned mail follow-up capability
- **THEN** the command fails with explicit availability guidance
- **AND THEN** it does not silently claim that the mailbox action succeeded
