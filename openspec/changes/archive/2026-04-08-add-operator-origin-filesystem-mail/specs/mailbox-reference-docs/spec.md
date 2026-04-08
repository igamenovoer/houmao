## ADDED Requirements

### Requirement: Mailbox reference docs explain operator-origin filesystem mail and the reserved sender namespace
The mailbox reference documentation SHALL explain the operator-origin filesystem-mail path and the reserved Houmao sender namespace.

At minimum, that documentation SHALL explain:

- the default managed-agent mailbox address policy `<agentname>@houmao.localhost`,
- the reservation of `HOUMAO-*` mailbox local parts for Houmao-owned system principals,
- the reserved operator sender `HOUMAO-operator@houmao.localhost`,
- the distinct operator-origin `post` workflow versus ordinary mailbox `send`,
- the one-way no-reply semantics for operator-origin messages,
- the explicit v1 boundary that operator-origin mail is filesystem-only and unsupported for `stalwart`.

#### Scenario: Reader can distinguish ordinary send from operator-origin post
- **WHEN** a reader uses the mailbox reference to understand how an operator leaves a note for a managed agent
- **THEN** the docs explain the difference between ordinary mailbox `send` and operator-origin mailbox `post`
- **AND THEN** the docs identify `HOUMAO-operator@houmao.localhost` as the reserved system sender for that one-way workflow

#### Scenario: Reader sees the filesystem-only boundary for operator-origin mail
- **WHEN** a reader consults the mailbox reference for transport support of operator-origin mail
- **THEN** the docs state that operator-origin mail is supported for the filesystem transport in v1
- **AND THEN** the docs state explicitly that `stalwart` remains an unsupported stub boundary for that workflow
