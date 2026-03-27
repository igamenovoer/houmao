## ADDED Requirements

### Requirement: `houmao-mgr` renders expected mailbox-related operator failures without Python tracebacks
When a native `houmao-mgr` mailbox-management or gateway mail-notifier command hits an expected operator-facing failure, the CLI SHALL render that failure as explicit command-line error output rather than leaking a Python traceback from the top-level wrapper.

This SHALL apply at minimum to:

- `houmao-mgr agents mailbox register`
- `houmao-mgr agents mailbox unregister`
- `houmao-mgr agents mailbox status`
- `houmao-mgr agents mail ...`
- `houmao-mgr agents gateway mail-notifier status`
- `houmao-mgr agents gateway mail-notifier enable`
- `houmao-mgr agents gateway mail-notifier disable`

The wrapper SHALL preserve the command's non-zero exit behavior for those failures.
This requirement covers expected operator-facing failures such as explicit Click-style usage errors, manifest/runtime readiness errors, and gateway readiness errors that the command path already classifies as normal command failures.
The CLI SHALL NOT claim success or hide the failure reason; it SHALL surface the explicit operator-facing error text without the Python stack trace.

#### Scenario: Joined mailbox registration failure renders as a clean CLI error
- **WHEN** an operator runs `houmao-mgr agents mailbox register --agent-name alice --mailbox-root /tmp/shared-mail`
- **AND WHEN** the command fails with an expected operator-facing mailbox-registration error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as clean CLI error text without a Python traceback

#### Scenario: Gateway mail-notifier enable failure renders as a clean CLI error
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --agent-name alice --interval-seconds 60`
- **AND WHEN** the command fails with an expected operator-facing gateway notifier readiness error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as clean CLI error text without a Python traceback
