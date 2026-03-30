## 1. Shared CLI Confirmation Contract

- [x] 1.1 Add a shared overwrite-confirmation helper for selected `houmao-mgr` commands, including interactive prompt behavior and non-interactive `--yes` handling.
- [x] 1.2 Wire a new `--yes` option into the selected mailbox and project-easy specialist-create command surfaces without changing unrelated confirmations such as workspace-trust `--yolo`.

## 2. Mailbox Registration Flows

- [x] 2.1 Update generic `houmao-mgr mailbox register` to require confirmation before destructive replacement while preserving `safe`, `force`, and `stash` semantics.
- [x] 2.2 Update `houmao-mgr project mailbox register` to mirror the generic mailbox overwrite-confirmation contract after resolving the project mailbox root.
- [x] 2.3 Update `houmao-mgr agents mailbox register` to use the same overwrite-confirmation contract before replacing shared mailbox state or mutating the managed-session mailbox binding.
- [x] 2.4 Add mailbox-focused tests for interactive confirmation, declined overwrite, non-interactive conflict without `--yes`, and `--yes` success paths.

## 3. Project Easy Specialist Replacement

- [x] 3.1 Update `project easy specialist create` conflict handling so an existing specialist definition can be replaced after prompt confirmation or `--yes`.
- [x] 3.2 Ensure confirmed specialist replacement updates specialist-owned generated prompt/preset state while preserving shared auth and skill content.
- [x] 3.3 Add project-easy tests covering interactive replacement, non-interactive conflict failure without `--yes`, and non-prompted replacement with `--yes`.

## 4. Documentation And Verification

- [x] 4.1 Update CLI and workflow documentation for mailbox registration and `project easy specialist create` to describe overwrite confirmation and `--yes`.
- [x] 4.2 Run the relevant unit test suites for mailbox and project CLI flows and confirm the new behavior matches the updated specs.
