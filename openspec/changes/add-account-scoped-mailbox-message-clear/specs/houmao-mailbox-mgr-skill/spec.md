## ADDED Requirements

### Requirement: `houmao-mailbox-mgr` routes single-account message reset work to account-scoped message clear

The packaged `houmao-mailbox-mgr` skill SHALL route requests to remove delivered messages for one selected mailbox account while preserving mailbox accounts to the maintained account-scoped message clear command for the selected mailbox scope.

When the task targets one account under an arbitrary filesystem mailbox root, the skill SHALL use:

```text
houmao-mgr mailbox messages clear --address <full-address> [--mailbox-root <path>] [--dry-run] [--yes]
```

When the task targets one account under the selected project overlay mailbox root, the skill SHALL use:

```text
houmao-mgr project mailbox messages clear --address <full-address> [--dry-run] [--yes]
```

The skill SHALL continue to route all-account delivered-message resets to `houmao-mgr mailbox clear-messages` or `houmao-mgr project mailbox clear-messages`.

The skill SHALL distinguish account-scoped message clearing from `cleanup`: `cleanup` remains for inactive or stashed registration cleanup, while `messages clear --address` removes delivered message visibility for one active account.

The skill SHALL NOT instruct callers to hand-edit mailbox-root files for single-account message clearing when the maintained account-scoped command covers the request.

#### Scenario: Skill routes project-local single-account reset to project message clear

- **WHEN** the user asks to remove all mailbox messages for `alice@houmao.localhost` in the active project mailbox root while preserving accounts
- **THEN** the skill directs the caller to `houmao-mgr project mailbox messages clear --address alice@houmao.localhost`
- **AND THEN** it does not route the request to `project mailbox clear-messages`, `project mailbox cleanup`, or account unregister commands

#### Scenario: Skill routes arbitrary-root single-account reset to generic message clear

- **WHEN** the user asks to remove all mailbox messages for `alice@houmao.localhost` under an explicit filesystem mailbox root at `/tmp/shared-mail`
- **THEN** the skill directs the caller to `houmao-mgr mailbox messages clear --mailbox-root /tmp/shared-mail --address alice@houmao.localhost`
- **AND THEN** it does not recommend ad hoc deletion inside the mailbox root

#### Scenario: Skill keeps all-account reset on clear-messages

- **WHEN** the user asks to clear all delivered messages from the selected project mailbox root while preserving accounts
- **THEN** the skill directs the caller to `houmao-mgr project mailbox clear-messages`
- **AND THEN** it does not replace the all-account reset with `project mailbox messages clear --address`
