## 1. Managed Mailbox Operation

- [x] 1.1 Add an account-scoped clear result/request path in `src/houmao/mailbox/managed.py` that validates one active address before mutation.
- [x] 1.2 Implement deterministic target planning for selected-account projection artifacts, selected local mailbox state, retained shared canonical artifacts, last-projection canonical cleanup, managed-copy attachment cleanup, external `path_ref` preservation, and blocked unsafe paths.
- [x] 1.3 Apply account-scoped SQLite mutations so selected-account projections and local state are removed while other accounts' projections remain visible.
- [x] 1.4 Delete filesystem artifacts according to the planned target set and preserve mailbox registrations and account directories.
- [x] 1.5 Add managed-layer unit tests for dry-run, shared-message preservation, last-projection canonical deletion, managed-copy attachment cleanup, external `path_ref` preservation, and missing-address failure.

## 2. Generic Mailbox CLI

- [x] 2.1 Add a shared support wrapper in `src/houmao/srv_ctrl/commands/mailbox_support.py` that calls the account-scoped managed clear operation and emits a cleanup-style payload with account-scoped scope metadata.
- [x] 2.2 Add `houmao-mgr mailbox messages clear --address <full-address> [--mailbox-root <path>] [--dry-run] [--yes]` in `src/houmao/srv_ctrl/commands/mailbox.py`.
- [x] 2.3 Reuse the existing destructive confirmation behavior so apply requires `--yes` non-interactively and dry-run never prompts.
- [x] 2.4 Add generic CLI tests for help output, dry-run payloads, non-interactive confirmation failure, successful selected-account clearing, and missing active account failure.

## 3. Project Mailbox CLI

- [x] 3.1 Add `houmao-mgr project mailbox messages clear --address <full-address> [--dry-run] [--yes]` in `src/houmao/srv_ctrl/commands/project_mailbox.py`.
- [x] 3.2 Reuse selected-overlay mailbox root resolution and selected-overlay failure wording for the project wrapper.
- [x] 3.3 Add project CLI tests for selected overlay scope, shared global root isolation, selected-account clear behavior, help output, and uninitialized-overlay failure wording.

## 4. Skill Guidance

- [x] 4.1 Update `houmao-mailbox-mgr` action guidance so single-account delivered-message reset routes to `mailbox messages clear --address` or `project mailbox messages clear --address`.
- [x] 4.2 Keep all-account delivered-message reset guidance on the existing `clear-messages` commands.
- [x] 4.3 Update system skill tests to assert the new account-scoped command guidance is packaged.

## 5. Verification

- [x] 5.1 Run focused mailbox managed and CLI unit tests.
- [x] 5.2 Run focused system skill tests.
- [x] 5.3 Run `pixi run lint` and `pixi run typecheck`, or document any environment blocker.
- [x] 5.4 Run `openspec status --change add-account-scoped-mailbox-message-clear` and confirm the change is apply-ready.
