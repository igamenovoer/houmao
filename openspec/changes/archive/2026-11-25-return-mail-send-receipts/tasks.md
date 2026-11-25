# Tasks

## 1. Mail Write Receipts

- [x] 1.1 Add the version-1 receipt projection for `send`, `reply`, and `post` at the manager CLI boundary. Test one dispatch through supported pair, gateway, and manager-direct routes with pinned channel and binding fixtures. Verify the replying agent's actual envelope and separate parent reference. Verify that an operator post identifies the operator and recipient binding separately.
- [x] 1.2 Project TUI send and reply outcomes into non-authoritative receipts. Test a transcript preview, existing non-success statuses, and a transport error with prior-commit evidence. Assert that no preview becomes a verified reference and no write is dispatched again. Check that post fails when authoritative access is unavailable.
- [x] 1.3 Render mail receipts in plain, fancy, and JSON using the same fields. Test both CLI scopes, multiple To and Cc addresses, and long opaque references. Check that each format shows the full reference without the message body or attachment details.
- [x] 1.4 Migrate repository CLI JSON consumers. Update `docs/reference/cli/agents-mail.md`, mailbox workflows, and `houmao-agent-email-comms` with first-call confirmation and read-only lookup. Verify the examples use `peek` on the source binding for send and reply and the target binding for post. Verify existing gateway and pair mail contract tests.

## 2. Gateway Prompt Receipts

- [x] 2.1 Render the existing gateway prompt result in plain, fancy, and JSON. Test managed headless queueing, native Web queueing, live handoff, optional identifiers, and a structured refusal. Verify each accepted invocation calls prompt control once and each refusal retains structured diagnostics and a nonzero exit.
- [x] 2.2 Document prompt receipt fields and supported read-only observation in the CLI reference and `houmao-agent-messaging` skill. Verify the examples distinguish a saved turn ID or service request lookup from limited Web and TUI evidence.

## 3. Memo Write Receipts

- [x] 3.1 Return a memo write receipt for scoped `set` and `append` on local and pair paths. Test the three output modes and check that a single append followed by `memo show` contains one addition. Verify the local receipt requires no memo reread and that the existing HTTP response contract still passes.
- [x] 3.2 Migrate repository CLI consumers and update the managed memory guide and `houmao-memory-mgr` skill. Verify the examples use the correct scope, acknowledge the write from the receipt, and inspect content through `memo show`.

## 4. Reminder Update Receipts

- [x] 4.1 Emit a compact `reminders set` receipt from the update response. Test field preservation and relative placement before the write. Make the list stub fail after a successful update and verify all formats still emit the saved ID and schedule without a post-update request.
- [x] 4.2 Migrate any repository CLI consumers and update CLI, gateway reminder, and packaged reminder guidance. Verify that `reminders get` and `list` are the documented reads for payloads and effective selection.

## 5. Browser Outcome

- [x] 5.1 Project the owner-local `open-browser` result to serializable fields. Stub the browser open and verify one call and the same safe fields in each output mode. Test stale owner rejection without invoking the opener. Update the Kimi Web CLI example to show the outcome fields.

## 6. Integration Verification

- [x] 6.1 Exercise scoped record-backed mail writes and read-only inspection with synthetic mail on explicitly isolated tmux sockets. Confirm one send, reply, and supported post per invocation, unchanged read state during `peek`, and rejection when the binding differs from the receipt.
- [x] 6.2 Run affected CLI, mailbox, gateway, and skill suites through Pixi. Run lint, type checking, and strict OpenSpec validation.
