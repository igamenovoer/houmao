# Decide What To Read

This gateway surface does not require a separate read route for ordinary mailbox work.

Use `POST /v1/mail/check` to inspect the current unread queue, then choose which `message_ref` to act on next.

Treat `message_ref` and `thread_ref` as opaque identifiers.

When multiple unread messages exist:
- use the unread headers returned by the prompt and `check`,
- choose the message or messages to inspect,
- re-check if the unread snapshot may have changed before taking more actions.
