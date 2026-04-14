# Root Selection And Lane Choice

Use this reference when the mailbox-admin task could land on more than one maintained lane.

## Choose The Lane

- Use `houmao-mgr mailbox ...` when the user targets one arbitrary filesystem mailbox root, passes `--mailbox-root`, or wants mailbox state outside the project overlay default.
- Use `houmao-mgr project mailbox ...` when the user explicitly wants the active project mailbox root or `.houmao/mailbox`.
- Use `houmao-mgr agents mailbox ...` when the user wants to inspect, add, or remove late filesystem mailbox support on one existing local managed agent.

## Root Defaults

- Generic `houmao-mgr mailbox ...` commands are project-aware: when `--mailbox-root` is omitted and `HOUMAO_GLOBAL_MAILBOX_DIR` is unset, the maintained command surface can resolve the active project mailbox root.
- `houmao-mgr project mailbox ...` intentionally fixes the target to the active overlay mailbox root.
- `houmao-mgr agents mailbox register` accepts an optional `--mailbox-root`, but it still belongs to the existing-agent late-binding lane rather than the mailbox-root lifecycle lane.

## Boundary

- Root lifecycle and account lifecycle belong to `mailbox` or `project mailbox`.
- Actor-scoped mailbox participation belongs to `houmao-agent-email-comms`.
- Notifier-driven open-mail rounds belong to `houmao-process-emails-via-gateway`.
