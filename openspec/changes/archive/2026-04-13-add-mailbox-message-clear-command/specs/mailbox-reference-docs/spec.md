## ADDED Requirements

### Requirement: Mailbox reference documentation explains the delivered-message clear workflow
The mailbox reference documentation SHALL document the supported delivered-message clear workflow for filesystem mailbox roots.

At minimum, the documentation SHALL explain:

- `houmao-mgr mailbox clear-messages` for an arbitrary resolved mailbox root,
- `houmao-mgr project mailbox clear-messages` for the selected project overlay mailbox root,
- that `clear-messages` removes delivered message content and derived message state while preserving mailbox account registrations,
- that `mailbox cleanup` remains registration cleanup and does not delete canonical messages,
- that external `path_ref` attachment targets are not deleted by message clearing,
- that the command supports dry-run preview and explicit destructive confirmation.

#### Scenario: Reader can choose between cleanup and clear-messages
- **WHEN** an operator reads the mailbox reference docs while trying to remove all delivered emails from a mailbox root
- **THEN** the docs identify `clear-messages` as the maintained command for delivered-message reset
- **AND THEN** the docs state that `cleanup` is not the command for deleting canonical mail

#### Scenario: Reader sees account preservation and attachment boundaries
- **WHEN** an operator reads the message-clear documentation
- **THEN** the docs explain that mailbox account registrations remain registered after message clearing
- **AND THEN** the docs explain that external `path_ref` attachment targets are not deleted
