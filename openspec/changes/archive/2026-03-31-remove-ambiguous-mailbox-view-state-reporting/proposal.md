## Why

`houmao-mgr mailbox messages ...` and `houmao-mgr project mailbox messages ...` currently report `read`, `starred`, `archived`, and `deleted` as though those fields were authoritative message metadata. They are actually mailbox-local participant view state, and the current implementation can already disagree with manager-owned read-state because the admin payload reads shared-root `mailbox_state` while runtime mutations land in mailbox-local `message_state`.

Even when those command families are scoped to one explicit mailbox address, the reported fields are still participant-local mutable workflow state rather than canonical mailbox-root facts. That makes the current contract conceptually wrong even if the storage layers were fully synchronized.

## What Changes

- **BREAKING** Remove `read`, `starred`, `archived`, and `deleted` from `houmao-mgr mailbox messages list|get` JSON payloads.
- **BREAKING** Remove `read`, `starred`, `archived`, and `deleted` from `houmao-mgr project mailbox messages list|get` JSON payloads.
- Clarify those command families as structural mailbox-root inspection surfaces that return canonical message metadata plus address-scoped projection metadata, not participant-local mutable view state.
- Keep participant-local read or unread follow-up on actor-scoped mail surfaces such as `houmao-mgr agents mail ...` instead of implying a single authoritative read status on mailbox administration commands.
- Revise docs and end-to-end testcases that currently treat mailbox admin or project mailbox inspection as the supported completion boundary for read-state verification.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: root-level and project-local mailbox message inspection stop reporting participant-local mutable mailbox view-state fields and remain structural or administrative inspection surfaces.

## Impact

- `src/houmao/srv_ctrl/commands/mailbox_support.py`
- `src/houmao/srv_ctrl/commands/mailbox.py`
- `src/houmao/srv_ctrl/commands/project.py`
- mailbox CLI tests and project mailbox tests that currently assert `read`-style fields
- mailbox reference docs and testcase notes that currently imply those admin surfaces can report authoritative read state
- gateway/mailbox testcases that currently require `project mailbox messages list|get` to report `read: true`
