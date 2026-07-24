# Mode Vocabulary

Use this reference when mailbox registration or deregistration mode semantics matter.

## Registration Modes

- `safe`
  keep existing durable mailbox state safe and fail instead of destructively replacing it without confirmation
- `force`
  replace existing durable mailbox state when the maintained command allows it
- `stash`
  preserve the displaced state in stashed form before replacing it

Registration commands that would replace existing durable state prompt before destructive replacement on interactive terminals and accept `--yes` for non-interactive confirmation.

## Deregistration Modes

- `deactivate`
  remove the active registration while preserving recoverable mailbox state
- `purge`
  remove the registration more aggressively when the operator explicitly wants that stronger cleanup posture

## Cleanup And Repair Posture

- `mailbox cleanup` works on inactive or stashed registrations and preserves canonical `messages/` history.
- `mailbox repair` rebuilds filesystem mailbox index state and can clean or quarantine staging artifacts depending on the selected flags.
