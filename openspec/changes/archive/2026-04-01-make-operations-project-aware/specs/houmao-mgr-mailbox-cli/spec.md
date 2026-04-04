## ADDED Requirements

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

## MODIFIED Requirements

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
