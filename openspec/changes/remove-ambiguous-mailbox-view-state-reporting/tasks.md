## 1. CLI Contract Cleanup

- [ ] 1.1 Remove `read`, `starred`, `archived`, and `deleted` from `list_mailbox_messages()` and `get_mailbox_message()` while keeping canonical and projection metadata intact.
- [ ] 1.2 Keep `houmao-mgr mailbox messages ...` and `houmao-mgr project mailbox messages ...` aligned on the same structural inspection helper contract and adjust command/help wording if it still implies authoritative view-state reporting.

## 2. Verification And Docs

- [ ] 2.1 Update or add tests for root-level and project-local mailbox message inspection to assert the ambiguous participant-local view-state fields are absent.
- [ ] 2.2 Refresh mailbox CLI and reference docs that currently imply mailbox admin or project mailbox inspection can report authoritative read-state.
