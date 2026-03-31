## MODIFIED Requirements

### Requirement: `project mailbox` resolves the current project's `.houmao/mailbox` root automatically

`houmao-mgr project mailbox ...` SHALL resolve the active overlay root in this order:

1. `HOUMAO_PROJECT_OVERLAY_DIR` when set,
2. nearest-ancestor project discovery from the caller's current working directory.

When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.

After resolving the active overlay root, `houmao-mgr project mailbox ...` SHALL apply the selected mailbox-root operation against:

```text
<overlay-root>/mailbox
```

The operator SHALL NOT need to pass `--mailbox-root` for ordinary project-scoped mailbox work.

If no project overlay is discovered under the selected overlay root, `project mailbox ...` SHALL fail explicitly rather than silently falling back to the shared global mailbox root.

#### Scenario: Register uses the env-selected project mailbox root
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project mailbox register --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice` from `/repo/subdir`
- **THEN** the command applies mailbox registration against `/tmp/ci-overlay/mailbox`
- **AND THEN** the operator does not need to provide an explicit `--mailbox-root`

#### Scenario: Messages list reads from the env-selected project mailbox root
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/mailbox` contains an active mailbox registration for `AGENTSYS-alice@agents.localhost`
- **AND WHEN** an operator runs `houmao-mgr project mailbox messages list --address AGENTSYS-alice@agents.localhost` from `/repo`
- **THEN** the command lists messages for that address from `/tmp/ci-overlay/mailbox`
- **AND THEN** it does not inspect the shared global mailbox root instead

#### Scenario: Missing overlay under env-selected overlay root fails clearly
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` does not exist
- **AND WHEN** an operator runs `houmao-mgr project mailbox status`
- **THEN** the command fails explicitly
- **AND THEN** it does not silently inspect the shared global mailbox root

#### Scenario: Register uses the discovered project mailbox root
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project mailbox register --address AGENTSYS-alice@agents.localhost --principal-id AGENTSYS-alice` from `/repo/subdir`
- **THEN** the command applies mailbox registration against `/repo/.houmao/mailbox`
- **AND THEN** the operator does not need to provide an explicit `--mailbox-root`
