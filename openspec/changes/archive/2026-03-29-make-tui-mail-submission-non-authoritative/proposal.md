## Why

The current mailbox command contract still overclaims what a TUI-mediated LLM turn can prove. Live testing showed the mailbox message can be delivered and a fresh sentinel block can be visibly present in tmux while the manager command still hangs or fails because the TUI observer cannot recover one exact active-request result surface.

`houmao-mgr` should not treat precise TUI transcript parsing as mailbox truth. For manager-owned direct or gateway-backed execution, Houmao can return authoritative mailbox success or failure. For TUI-mediated fallback, the honest contract is request lifecycle only: submitted, rejected, interrupted, or TUI error, with mailbox outcome verified through manager-owned follow-up or transport-native state.

## What Changes

- Revise manager mailbox command semantics so TUI-mediated `houmao-mgr` mail operations are non-authoritative and return submission lifecycle state rather than mailbox success inferred from transcript parsing.
- Keep authoritative mailbox success and failure only for manager-owned direct execution paths such as direct local execution or gateway-backed execution where Houmao owns the protocol interaction.
- Reclassify TUI parsing as state-tracking and preview support, not the correctness boundary for `houmao-mgr` mailbox operations.
- Update local `houmao-mgr agents mail ...` and the planned self-scoped `houmao-mgr mail ...` design so fallback to agent-prompt mediation does not require exact structured mailbox-result parsing to complete the manager command.
- Update runtime and mailbox docs to distinguish:
  - authoritative results from manager-owned execution,
  - non-authoritative request submission results from TUI-mediated execution,
  - operator verification paths such as mailbox status/check or transport-native inspection.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `brain-launch-runtime`: revise runtime mail command semantics so TUI-mediated mailbox turns are not required to yield authoritative mailbox success from exact sentinel parsing when used through manager-owned command surfaces.
- `houmao-srv-ctrl-native-cli`: revise `houmao-mgr` mailbox command semantics to distinguish manager-owned verified execution from TUI-mediated submission-only fallback.
- `mailbox-reference-docs`: revise mailbox docs so verification guidance is based on manager-owned or protocol-owned state, not on exact TUI reply-schema recovery.

## Impact

- Affected code includes manager mail command routing, runtime mail command result handling, TUI-backed mailbox turn monitoring, and mailbox CLI/docs.
- This is a contract change for mailbox command outcomes, especially for local TUI-mediated managed-agent workflows.
- Existing sentinel parsing may remain useful for chat preview, turn-state tracking, and optional diagnostics, but it is no longer the mailbox correctness boundary for manager commands.
