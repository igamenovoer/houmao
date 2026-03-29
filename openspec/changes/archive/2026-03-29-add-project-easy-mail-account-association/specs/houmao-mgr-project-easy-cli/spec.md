## MODIFIED Requirements

### Requirement: `project easy instance launch` derives provider from one specialist and launches one runtime instance

`houmao-mgr project easy instance launch --specialist <specialist> --name <instance>` SHALL launch one managed agent by resolving the compiled specialist definition and delegating to the existing native managed-agent launch flow.

The launch provider SHALL be derived from the specialist's selected tool:

- `claude` -> `claude_code`
- `codex` -> `codex`
- `gemini` -> `gemini_cli`

The operator SHALL NOT need to provide the provider identifier separately when launching an instance from a specialist.

When launch-time mailbox association is requested, the command SHALL accept these high-level mailbox inputs:

- `--mail-transport <filesystem|email>`
- `--mail-root <dir>` when `--mail-transport filesystem`
- optional `--mail-account-dir <dir>` when `--mail-transport filesystem`

When `--mail-transport filesystem` is selected and `--mail-account-dir` is omitted, the command SHALL launch the instance with an in-root filesystem mailbox account for that instance's mailbox identity under the selected mailbox root.

When `--mail-transport filesystem` is selected and `--mail-account-dir` is provided, the command SHALL launch the instance with a symlink-backed filesystem mailbox account whose shared-root mailbox entry points at the requested mailbox account directory.

When `--mail-transport email` is selected in this change, the command SHALL fail clearly as not implemented and SHALL exit non-zero before creating a managed-agent session.

If mailbox validation or mailbox bootstrap fails during a mailbox-enabled easy launch, the command SHALL fail clearly and SHALL NOT report a successful managed-agent launch.

#### Scenario: Specialist launch derives the Codex provider automatically
- **WHEN** specialist `researcher` was created with tool `codex`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **THEN** the command launches the managed agent using the compiled `researcher` role and the derived `codex` provider
- **AND THEN** the operator does not need to pass `--provider codex` explicitly

#### Scenario: Filesystem easy launch binds an in-root mailbox account
- **WHEN** specialist `researcher` was created with tool `codex`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --mail-transport filesystem --mail-root /tmp/houmao-mail`
- **THEN** the command launches the managed agent successfully
- **AND THEN** the launched instance is associated with a filesystem mailbox account under the selected mailbox root for that instance identity

#### Scenario: Filesystem easy launch binds a symlink-backed private mailbox directory
- **WHEN** specialist `researcher` was created with tool `codex`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --mail-transport filesystem --mail-root /tmp/houmao-mail --mail-account-dir /tmp/private-mail/repo-research-1`
- **THEN** the command launches the managed agent successfully
- **AND THEN** the launched instance is associated with a symlink-backed filesystem mailbox account under `/tmp/houmao-mail`
- **AND THEN** the concrete mailbox account directory is `/tmp/private-mail/repo-research-1`

#### Scenario: Instance launch requires both specialist and instance identity
- **WHEN** an operator requests `project easy instance launch`
- **AND WHEN** the operator omits either `--specialist` or `--name`
- **THEN** the command fails clearly before launch
- **AND THEN** the error explains that instance launch requires both the specialist selector and the concrete instance identity

#### Scenario: Email transport fails fast before launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --mail-transport email`
- **THEN** the command exits non-zero
- **AND THEN** the error reports that the real-email easy-launch path is not implemented yet
- **AND THEN** no managed-agent session is created

### Requirement: `project easy instance list/get/stop` presents runtime state by specialist and wraps existing runtime stop control

`houmao-mgr project easy instance list` SHALL present launched managed agents as instances, annotated by their originating specialist when that specialist can be resolved.

`houmao-mgr project easy instance get --name <instance>` SHALL report the current managed-agent runtime summary plus the originating specialist metadata when available.

`houmao-mgr project easy instance stop --name <instance>` SHALL stop one managed-agent instance after verifying that the resolved runtime session belongs to the current project overlay.

`project easy instance stop` SHALL delegate to the existing canonical managed-agent stop implementation rather than directly killing the resolved tmux session.

This change SHALL NOT define `project easy instance stop` semantics that differ from the current managed-agent stop behavior.

The instance view SHALL be derived from existing managed-agent runtime state and SHALL NOT require a second persisted per-instance config contract in v1.

When the resolved runtime state includes a mailbox association, `project easy instance get` SHALL report the effective mailbox summary, including:

- the high-level mailbox transport,
- the mailbox address,
- the shared mailbox root,
- the mailbox kind,
- the resolved concrete mailbox directory.

`project easy instance list` SHALL surface whether each instance currently has a mailbox association and MAY present that information as a compact mailbox summary.

The `instance` group SHALL own launch, stop, and runtime inspection, while the `specialist` group remains limited to reusable configuration management.

#### Scenario: Instance list groups launched agents by specialist
- **WHEN** a launched managed agent was started from specialist `researcher`
- **AND WHEN** an operator runs `houmao-mgr project easy instance list`
- **THEN** the command reports that managed agent as an instance of `researcher`
- **AND THEN** the command derives that view from the existing runtime state rather than from a second stored instance definition

#### Scenario: Instance get reports the effective mailbox association
- **WHEN** launched instance `repo-research-1` was started with a filesystem mailbox association
- **AND WHEN** an operator runs `houmao-mgr project easy instance get --name repo-research-1`
- **THEN** the command reports the instance's runtime summary and originating specialist metadata
- **AND THEN** it also reports the effective mailbox transport, mailbox address, mailbox root, mailbox kind, and resolved mailbox directory from runtime-derived state

#### Scenario: Instance stop wraps the canonical managed-agent stop path
- **WHEN** launched instance `repo-research-1` belongs to the current project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy instance stop --name repo-research-1`
- **THEN** the command verifies that the resolved managed-agent manifest belongs to the discovered project overlay
- **AND THEN** it stops the instance by delegating to the existing managed-agent stop implementation rather than by directly killing tmux from the project CLI

#### Scenario: Instance stop rejects a managed agent outside the current project overlay
- **WHEN** managed agent `repo-research-1` resolves successfully
- **AND WHEN** its manifest does not belong to the discovered project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy instance stop --name repo-research-1`
- **THEN** the command fails clearly
- **AND THEN** it does not delegate stop control for a managed agent outside the current project overlay
