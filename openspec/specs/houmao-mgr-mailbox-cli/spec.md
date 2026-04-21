## Purpose
Define the local `houmao-mgr mailbox` command family for filesystem mailbox administration workflows that do not require `houmao-server`.
## Requirements
### Requirement: `houmao-mgr mailbox` exposes local filesystem mailbox administration commands
`houmao-mgr` SHALL expose a top-level `mailbox` command family for local filesystem mailbox administration that does not require `houmao-server`.

At minimum, that family SHALL include:

- `init`
- `status`
- `register`
- `unregister`
- `repair`
- `cleanup`
- `clear-messages`
- `export`
- `accounts`
- `messages`

The family SHALL target the filesystem mailbox transport only in v1.

#### Scenario: Operator sees the local mailbox administration commands
- **WHEN** an operator runs `houmao-mgr mailbox --help`
- **THEN** the help output lists `init`, `status`, `register`, `unregister`, `repair`, `cleanup`, `clear-messages`, `export`, `accounts`, and `messages`
- **AND THEN** the command family is presented as a local mailbox administration surface rather than a server-backed API surface

### Requirement: `houmao-mgr mailbox accounts` inspects mailbox registrations as operator-facing accounts
`houmao-mgr mailbox accounts` SHALL expose inspection commands over mailbox registrations under one resolved mailbox root.

At minimum, `accounts` SHALL expose:

- `list`
- `get`

`accounts list` SHALL enumerate registered mailbox addresses together with their registration state.

`accounts get --address <full-address>` SHALL report one mailbox registration, including the selected address, owner principal id when available, registration state, and mailbox path metadata.

#### Scenario: Accounts list reports registered mailbox addresses
- **WHEN** an operator runs `houmao-mgr mailbox accounts list --mailbox-root /tmp/shared-mail`
- **AND WHEN** that root contains active and inactive registrations
- **THEN** the command returns those registered mailbox addresses with their lifecycle state
- **AND THEN** the operator does not need to inspect mailbox root files manually to discover registered addresses

#### Scenario: Accounts get reports one selected mailbox registration
- **WHEN** `/tmp/shared-mail` contains an active registration for `AGENTSYS-alice@agents.localhost`
- **AND WHEN** an operator runs `houmao-mgr mailbox accounts get --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost`
- **THEN** the command reports the selected address and its registration metadata
- **AND THEN** the result identifies the mailbox path for that registration

### Requirement: `houmao-mgr mailbox messages` lists and gets mailbox content for one registered address
`houmao-mgr mailbox messages` SHALL expose direct read-only mailbox content inspection for one selected registered mailbox address under one resolved mailbox root.

At minimum, `messages` SHALL expose:

- `list`
- `get`

`messages list --address <full-address>` SHALL return message summaries for the selected mailbox address.

`messages get --address <full-address> --message-id <message-id>` SHALL return the content and metadata for one selected message visible to that mailbox address.

The summary payload for `messages list` SHALL include enough metadata to select one message for `messages get`, including `message_id`.

#### Scenario: Messages list returns mailbox-visible summaries for one address
- **WHEN** `/tmp/shared-mail` contains an active mailbox registration for `AGENTSYS-alice@agents.localhost`
- **AND WHEN** mailbox-visible messages exist for that address
- **AND WHEN** an operator runs `houmao-mgr mailbox messages list --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost`
- **THEN** the command returns message summaries for that selected address
- **AND THEN** each summary includes a `message_id` suitable for later message retrieval

#### Scenario: Messages get returns the selected message content
- **WHEN** `/tmp/shared-mail` contains mailbox-visible message `msg-123` for `AGENTSYS-alice@agents.localhost`
- **AND WHEN** an operator runs `houmao-mgr mailbox messages get --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --message-id msg-123`
- **THEN** the command returns the content and metadata for `msg-123`
- **AND THEN** the operator does not need to inspect the canonical mailbox document directly on disk

### Requirement: `houmao-mgr mailbox init` bootstraps or validates one filesystem mailbox root
`houmao-mgr mailbox init` SHALL bootstrap or validate one filesystem mailbox root using the filesystem mailbox bootstrap contract.

The effective mailbox root SHALL resolve from:

1. explicit `--mailbox-root`,
2. `HOUMAO_GLOBAL_MAILBOX_DIR`,
3. the active project overlay mailbox root,
4. bootstrap `<cwd>/.houmao/mailbox` when no overlay exists and no stronger override applies.

A successful bootstrap SHALL create or validate the v1 filesystem mailbox layout, including protocol version, shared SQLite catalog, rules assets, mailbox directories root, locks root, and staging root.

#### Scenario: Init without overrides uses the active overlay mailbox root
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr mailbox init` without `--mailbox-root`
- **AND WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is unset
- **THEN** the command bootstraps or validates `/repo/.houmao/mailbox`
- **AND THEN** it does not bootstrap a shared mailbox root under `~/.houmao/`

### Requirement: `houmao-mgr mailbox status` reports filesystem mailbox root health and summary state
`houmao-mgr mailbox status` SHALL inspect one filesystem mailbox root and return a structured summary of its health and stored state.

At minimum, the summary SHALL report:

- the resolved mailbox root,
- whether the root is bootstrapped and supported,
- the protocol version when available,
- counts of active, inactive, and stashed mailbox registrations,
- whether shared mailbox structural state is readable.

#### Scenario: Operator inspects a healthy mailbox root
- **WHEN** an operator runs `houmao-mgr mailbox status --mailbox-root /tmp/shared-mail`
- **AND WHEN** `/tmp/shared-mail` is a healthy bootstrapped filesystem mailbox root
- **THEN** the command returns a structured summary for that root
- **AND THEN** the summary reports readable mailbox state rather than requiring the operator to inspect files manually

### Requirement: `houmao-mgr mailbox register` and `unregister` expose operator mailbox lifecycle control
`houmao-mgr mailbox register` and `houmao-mgr mailbox unregister` SHALL expose operator-facing mailbox lifecycle control for filesystem mailbox addresses.

`register` SHALL accept a full mailbox address and owner principal id, SHALL use explicit registration modes, and SHALL accept `--yes` for non-interactive overwrite confirmation.
`unregister` SHALL accept a full mailbox address and SHALL use explicit deregistration modes, defaulting to `deactivate`.

When a requested registration path would replace existing durable mailbox state or an existing mailbox entry artifact, the CLI SHALL require explicit operator confirmation before applying the destructive replacement.
This confirmation requirement SHALL apply whether destructive replacement was requested explicitly through `--mode force` or reached from the default safe registration flow after conflict detection.
When `--yes` is present, the CLI SHALL apply the overwrite-confirmed registration path without prompting.
When `--yes` is absent and an interactive terminal is available, the CLI SHALL prompt the operator before applying the destructive replacement.
When `--yes` is absent and no interactive terminal is available, the CLI SHALL fail clearly before destructive replacement and direct the operator to rerun with `--yes` or choose a non-destructive registration mode.
If the operator declines the overwrite prompt, the command SHALL abort without replacing the existing durable mailbox state.
The CLI SHALL preserve the established `safe`, `force`, and `stash` registration-mode vocabulary; this change SHALL NOT reinterpret `stash` as an automatic fallback for overwrite conflicts.

#### Scenario: Operator registers an in-root mailbox address safely
- **WHEN** an operator runs `houmao-mgr mailbox register --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice`
- **AND WHEN** no destructive replacement is required
- **THEN** the command creates or reuses the active in-root mailbox registration for that address using safe registration semantics
- **AND THEN** the result reports the resulting active registration identity

#### Scenario: Operator confirms overwrite after a safe registration conflict
- **WHEN** an operator runs `houmao-mgr mailbox register --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice`
- **AND WHEN** the default safe registration flow detects a replaceable conflict for that mailbox address
- **AND WHEN** an interactive terminal is available
- **AND WHEN** the operator confirms overwrite
- **THEN** the command applies destructive replacement semantics for that request
- **AND THEN** the result reports the resulting active registration identity

#### Scenario: Operator declines overwrite after a safe registration conflict
- **WHEN** an operator runs `houmao-mgr mailbox register --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice`
- **AND WHEN** the default safe registration flow detects a replaceable conflict for that mailbox address
- **AND WHEN** an interactive terminal is available
- **AND WHEN** the operator declines overwrite
- **THEN** the command aborts
- **AND THEN** the existing mailbox state remains unchanged

#### Scenario: Non-interactive conflict without yes fails before replacement
- **WHEN** an operator runs `houmao-mgr mailbox register --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice`
- **AND WHEN** the requested registration path would replace existing durable mailbox state
- **AND WHEN** no interactive terminal is available
- **AND WHEN** `--yes` is not present
- **THEN** the command fails clearly before destructive replacement
- **AND THEN** the existing mailbox state remains unchanged

#### Scenario: Yes skips overwrite prompt
- **WHEN** an operator runs `houmao-mgr mailbox register --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice --yes`
- **AND WHEN** the requested registration path would replace existing durable mailbox state
- **THEN** the command applies the overwrite-confirmed registration path without prompting
- **AND THEN** the result reports the resulting active registration identity

#### Scenario: Operator unregisters a mailbox address without deleting canonical history
- **WHEN** an operator runs `houmao-mgr mailbox unregister --mailbox-root /tmp/shared-mail --address AGENTSYS-alice@agents.localhost`
- **THEN** the command deactivates the active mailbox registration for that address by default
- **AND THEN** future delivery to that address requires a later active registration
- **AND THEN** canonical mailbox history remains preserved

### Requirement: `houmao-mgr mailbox repair` rebuilds filesystem mailbox index state locally
`houmao-mgr mailbox repair` SHALL rebuild one filesystem mailbox root's shared index state locally without requiring `houmao-server`.

The repair flow SHALL use the filesystem mailbox repair contract and SHALL report recovered registration or message state in a structured result.

#### Scenario: Operator repairs a mailbox root locally
- **WHEN** an operator runs `houmao-mgr mailbox repair --mailbox-root /tmp/shared-mail`
- **THEN** the command rebuilds filesystem mailbox index state for `/tmp/shared-mail`
- **AND THEN** the result reports repair outcomes without requiring manual SQLite intervention

### Requirement: `houmao-mgr mailbox cleanup` removes inactive or stashed registrations without deleting canonical messages
`houmao-mgr mailbox cleanup` SHALL clean up no-longer-relevant filesystem mailbox registrations under one resolved mailbox root without requiring `houmao-server`.

The effective mailbox root SHALL resolve from:

1. explicit `--mailbox-root`,
2. `HOUMAO_GLOBAL_MAILBOX_DIR`,
3. the default shared mailbox root.

The command SHALL operate only on registrations whose status is `inactive` or `stashed`.

The command SHALL preserve:

- active mailbox registrations,
- canonical mailbox messages under `messages/`,
- mailbox roots that need repair rather than destructive cleanup.

The command SHALL accept `--dry-run`. In dry-run mode, it SHALL report matching registration and artifact cleanup candidates without deleting them.

#### Scenario: Dry-run reports inactive or stashed cleanup candidates without deleting canonical mail
- **WHEN** an operator runs `houmao-mgr mailbox cleanup --mailbox-root /tmp/shared-mail --dry-run`
- **AND WHEN** the mailbox root contains inactive or stashed registrations
- **THEN** the command reports those registrations as cleanup candidates
- **AND THEN** it does not delete canonical messages under `messages/` during that dry-run

#### Scenario: Cleanup removes inactive or stashed registrations
- **WHEN** an operator runs `houmao-mgr mailbox cleanup --mailbox-root /tmp/shared-mail`
- **AND WHEN** the mailbox root contains inactive or stashed registrations
- **THEN** the command removes the matching inactive or stashed registration state
- **AND THEN** the result reports which registrations were removed

#### Scenario: Active registration is preserved during cleanup
- **WHEN** an operator runs `houmao-mgr mailbox cleanup --mailbox-root /tmp/shared-mail`
- **AND WHEN** the mailbox root still contains an active registration for one mailbox address
- **THEN** the command preserves that active registration
- **AND THEN** the cleanup result does not report the active mailbox as removed

### Requirement: `houmao-mgr mailbox clear-messages` clears delivered messages while preserving registrations
`houmao-mgr mailbox clear-messages` SHALL clear delivered filesystem mailbox message content under one resolved mailbox root without requiring `houmao-server`.

The effective mailbox root SHALL resolve using the same project-aware root-selection contract as the generic `houmao-mgr mailbox` family.

The command SHALL preserve:

- all mailbox registration rows and their active, inactive, or stashed lifecycle state,
- registered mailbox account directories and symlinked private mailbox account targets,
- mailbox root protocol, rules, locks, staging, and mailbox directory layout.

The command SHALL remove delivered mail content and derived message state, including:

- canonical mailbox messages under `messages/`,
- mailbox projection artifacts for cleared messages,
- shared index rows for messages, recipients, message attachments, projections, mailbox state, and thread summaries,
- mailbox-local `mailbox.sqlite` message and thread state for registered accounts,
- managed-copy attachment artifacts owned by the mailbox root for cleared messages.

The command SHALL NOT delete external `path_ref` attachment targets.

The command SHALL accept `--dry-run`. In dry-run mode, it SHALL report planned message-clear actions without deleting files or mutating SQLite state.

The command SHALL require explicit destructive confirmation before applying changes. When `--yes` is present, the command SHALL apply without prompting. When `--yes` is absent and an interactive terminal is available, the command SHALL prompt before clearing delivered messages. When `--yes` is absent and no interactive terminal is available, the command SHALL fail clearly before clearing messages and direct the operator to rerun with `--yes` or `--dry-run`.

The command SHALL be idempotent: rerunning it against an already-cleared mailbox root SHALL preserve registrations and report no remaining delivered messages to clear.

#### Scenario: Dry-run previews mailbox-wide message clearing
- **WHEN** an operator runs `houmao-mgr mailbox clear-messages --mailbox-root /tmp/shared-mail --dry-run`
- **AND WHEN** `/tmp/shared-mail` contains registered mailbox accounts and delivered messages
- **THEN** the command reports planned clearing of delivered messages and derived message state
- **AND THEN** it does not delete canonical message files, projection artifacts, account registrations, or mailbox-local state

#### Scenario: Yes clears messages and preserves accounts
- **WHEN** an operator runs `houmao-mgr mailbox clear-messages --mailbox-root /tmp/shared-mail --yes`
- **AND WHEN** `/tmp/shared-mail` contains active registered mailbox accounts and delivered messages
- **THEN** the command removes delivered message content and derived message state from the mailbox root
- **AND THEN** the active mailbox registrations remain registered for later delivery
- **AND THEN** the registered mailbox account directories remain present

#### Scenario: Non-interactive apply without yes fails before clearing
- **WHEN** an operator runs `houmao-mgr mailbox clear-messages --mailbox-root /tmp/shared-mail` without `--yes`
- **AND WHEN** no interactive terminal is available
- **THEN** the command fails clearly before deleting delivered message content
- **AND THEN** the failure tells the operator to rerun with `--yes` or `--dry-run`

#### Scenario: External attachment targets are preserved
- **WHEN** a delivered mailbox message references an external `path_ref` attachment target
- **AND WHEN** an operator runs `houmao-mgr mailbox clear-messages --mailbox-root /tmp/shared-mail --yes`
- **THEN** the command removes mailbox-owned message metadata for that attachment
- **AND THEN** it does not delete the external attachment target path

#### Scenario: Existing cleanup command remains registration-scoped
- **WHEN** an operator runs `houmao-mgr mailbox cleanup --mailbox-root /tmp/shared-mail`
- **THEN** the cleanup command remains limited to inactive or stashed registration cleanup
- **AND THEN** it does not clear delivered messages or canonical mailbox history

#### Scenario: Mailbox help lists the clear-messages command
- **WHEN** an operator runs `houmao-mgr mailbox --help`
- **THEN** the help output lists `clear-messages` alongside the maintained filesystem mailbox administration commands
- **AND THEN** the help output keeps `cleanup` and `clear-messages` as separate command verbs

### Requirement: `houmao-mgr mailbox export` writes a filesystem mailbox archive
`houmao-mgr mailbox export` SHALL export selected state from one resolved filesystem mailbox root into a portable archive directory without requiring `houmao-server`.

The command SHALL accept:

- `--output-dir <dir>`,
- either `--all-accounts` or one or more `--address <full-address>` values,
- `--symlink-mode materialize|preserve`.

The default `--symlink-mode` value SHALL be `materialize`.

The effective mailbox root SHALL resolve using the same project-aware root-selection contract as the generic `houmao-mgr mailbox` family.

When `--all-accounts` is present, the command SHALL export all mailbox registration rows and all canonical messages known to the shared mailbox index.

When one or more `--address` values are present, the command SHALL export registrations for those addresses and messages visible through projection rows for those registrations.

The command SHALL fail clearly when neither `--all-accounts` nor `--address` is provided.

The command SHALL fail clearly when `--all-accounts` and `--address` are both provided.

The command SHALL fail clearly when `--output-dir` already exists.

The command SHALL emit a structured payload identifying the resolved mailbox root, output directory, symlink mode, selected addresses, manifest path, summary counts, copied or materialized artifacts, skipped artifacts, and blocked artifacts.

#### Scenario: Export all accounts from an explicit mailbox root
- **WHEN** an operator runs `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir /tmp/archive --all-accounts`
- **AND WHEN** `/tmp/shared-mail` contains registered accounts and delivered messages
- **THEN** the command writes a mailbox export archive under `/tmp/archive`
- **AND THEN** the result reports the archive manifest path
- **AND THEN** the default archive contains no symlink artifacts

#### Scenario: Export selected accounts from a project-aware mailbox root
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr mailbox export --output-dir /tmp/archive --address alice@houmao.localhost`
- **AND WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is unset
- **THEN** the command exports selected account state from `/repo/.houmao/mailbox`
- **AND THEN** the command does not inspect the shared global mailbox root

#### Scenario: Export requires explicit account scope
- **WHEN** an operator runs `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir /tmp/archive`
- **THEN** the command fails clearly
- **AND THEN** the failure instructs the operator to choose `--all-accounts` or one or more `--address` values

#### Scenario: Export rejects conflicting account scope
- **WHEN** an operator runs `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir /tmp/archive --all-accounts --address alice@houmao.localhost`
- **THEN** the command fails clearly before exporting
- **AND THEN** it does not create or modify `/tmp/archive`

#### Scenario: Preserve mode is explicit
- **WHEN** an operator runs `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir /tmp/archive --all-accounts --symlink-mode preserve`
- **THEN** the command attempts to preserve supported archive-internal symlink relationships
- **AND THEN** the command reports the selected symlink mode in the structured payload

#### Scenario: Existing output directory fails
- **WHEN** `/tmp/archive` already exists
- **AND WHEN** an operator runs `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir /tmp/archive --all-accounts`
- **THEN** the command fails clearly before writing archive content
- **AND THEN** the command does not merge new export artifacts into the existing directory

### Requirement: `houmao-mgr mailbox` resolves mailbox roots project-aware by default
When a generic `houmao-mgr mailbox ...` command runs without an explicit `--mailbox-root` and without `HOUMAO_GLOBAL_MAILBOX_DIR`, the effective mailbox root SHALL resolve project-aware from the active project overlay as `<active-overlay>/mailbox`.

When no active project overlay exists and the command requires local mailbox state, the command SHALL ensure `<cwd>/.houmao` exists and use `<cwd>/.houmao/mailbox` as the resulting default mailbox root.

#### Scenario: Generic mailbox command uses the overlay-local mailbox root
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr mailbox status` without `--mailbox-root`
- **AND WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is unset
- **THEN** the command targets `/repo/.houmao/mailbox`
- **AND THEN** it does not fall back to a shared mailbox root under `~/.houmao/`

#### Scenario: Generic mailbox command bootstraps the missing overlay when mailbox state is needed
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr mailbox init` without `--mailbox-root`
- **AND WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is unset
- **THEN** the command ensures `<cwd>/.houmao` exists
- **AND THEN** it bootstraps `<cwd>/.houmao/mailbox` as the effective mailbox root

### Requirement: Generic mailbox help and rootless results describe project-aware mailbox selection
Maintained `houmao-mgr mailbox ...` help text and rootless result wording SHALL distinguish between an active project mailbox root and an explicit shared mailbox-root override.

When no explicit mailbox-root override wins and project context is active, operator-facing wording SHALL describe the resolved mailbox scope as the active project mailbox root.

When `--mailbox-root` or `HOUMAO_GLOBAL_MAILBOX_DIR` wins, operator-facing wording SHALL describe that scope as an explicit mailbox-root selection or shared mailbox-root override rather than as the active project mailbox root.

#### Scenario: Mailbox help text describes the active project mailbox root fallback
- **WHEN** an operator runs `houmao-mgr mailbox --help` or inspects a mailbox subcommand help page with `--mailbox-root`
- **THEN** the help output explains that rootless mailbox commands may default to the active project mailbox root
- **AND THEN** it does not present the shared mailbox root as the only maintained default

#### Scenario: Rootless mailbox bootstrap surfaces project-aware selection
- **WHEN** an operator runs a maintained rootless mailbox command in project context without `--mailbox-root`
- **AND WHEN** that invocation resolves mailbox state from the selected project overlay
- **THEN** the operator-facing result describes the resolved mailbox scope as the active project mailbox root
- **AND THEN** it does not describe that resolution as though the command had targeted an explicit shared mailbox-root override

### Requirement: `houmao-mgr mailbox` reflects the reserved operator mailbox account
The generic filesystem mailbox CLI SHALL reflect the reserved operator mailbox account `HOUMAO-operator@houmao.localhost`.

`houmao-mgr mailbox init` SHALL provision or confirm that reserved account for the resolved filesystem mailbox root.

`houmao-mgr mailbox accounts list|get` SHALL expose that reserved account as mailbox registration state instead of hiding it.

Generic destructive lifecycle commands SHALL protect that reserved account:

- `unregister` SHALL reject destructive removal of the reserved operator account by default,
- `cleanup` SHALL preserve the active reserved operator account.

#### Scenario: Generic mailbox init confirms the reserved operator account
- **WHEN** an operator runs `houmao-mgr mailbox init`
- **THEN** the resulting mailbox root state includes the reserved account `HOUMAO-operator@houmao.localhost`
- **AND THEN** later `accounts list` can inspect that account through the same mailbox-root CLI family

#### Scenario: Generic mailbox unregister rejects the reserved operator account
- **WHEN** an operator runs `houmao-mgr mailbox unregister --address HOUMAO-operator@houmao.localhost`
- **THEN** the command fails explicitly instead of removing the reserved system mailbox registration
- **AND THEN** the mailbox root continues preserving the operator-origin sender account

### Requirement: `houmao-mgr mailbox` renders expected mailbox-root state failures as actionable CLI errors

When a maintained `houmao-mgr mailbox ...` command that expects an existing supported filesystem mailbox root encounters an expected mailbox-root state failure, the command SHALL fail as explicit CLI error output rather than leaking a Python traceback.

This SHALL apply at minimum to mailbox commands that inspect or mutate existing mailbox-root state, including:

- `accounts list`
- `accounts get`
- `messages list`
- `messages get`
- `unregister`
- `repair`
- `cleanup`
- `clear-messages`
- `export`

Expected mailbox-root state failures include unsupported mailbox roots, missing protocol-version state, missing shared mailbox indexes, unreadable shared mailbox indexes, and missing active registrations.

When an inspection command such as `houmao-mgr mailbox accounts list` fails because the resolved mailbox root is missing its shared mailbox index, the error text SHALL direct the operator to run `houmao-mgr mailbox init` first.

#### Scenario: Accounts list on an uninitialized mailbox root fails as CLI error text

- **WHEN** an operator runs `houmao-mgr mailbox accounts list --mailbox-root /tmp/shared-mail`
- **AND WHEN** `/tmp/shared-mail` lacks the shared mailbox index required for account inspection
- **THEN** the command exits non-zero with explicit CLI error text
- **AND THEN** the error tells the operator to run `houmao-mgr mailbox init` first
- **AND THEN** the operator does not see a Python traceback

#### Scenario: Cleanup on an unsupported mailbox root fails as CLI error text

- **WHEN** an operator runs `houmao-mgr mailbox cleanup --mailbox-root /tmp/shared-mail`
- **AND WHEN** the resolved mailbox root is missing required bootstrap state or is otherwise unsupported
- **THEN** the command exits non-zero with explicit CLI error text for that mailbox root
- **AND THEN** the operator does not see a raw mailbox-domain exception traceback

