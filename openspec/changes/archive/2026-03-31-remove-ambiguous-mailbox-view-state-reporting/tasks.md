## 1. CLI Contract Cleanup

- [x] 1.1 Remove `read`, `starred`, `archived`, and `deleted` from `list_mailbox_messages()` and `get_mailbox_message()` while keeping canonical and projection metadata intact.
- [x] 1.2 Keep `houmao-mgr mailbox messages ...` and `houmao-mgr project mailbox messages ...` aligned on the same structural inspection helper contract and adjust command/help wording if it still implies authoritative view-state reporting.

## 2. Verification And Docs

- [x] 2.1 Update or add tests for root-level and project-local mailbox message inspection to assert the ambiguous participant-local view-state fields are absent.
- [x] 2.2 Refresh mailbox CLI and reference docs that currently imply mailbox admin or project mailbox inspection can report authoritative read-state.
- [x] 2.3 Revise end-to-end mailbox and gateway testcases that currently treat `houmao-mgr project mailbox messages list|get` as the completion authority for read-state; move those completion checks to actor-scoped `houmao-mgr agents mail ...` surfaces while keeping project mailbox inspection for structural verification only.
