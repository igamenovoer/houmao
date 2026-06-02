## ADDED Requirements

### Requirement: Project credentials are selected through the project command group
Project-backed credential management SHALL be exposed through:

```text
houmao-mgr project [--project-dir <dir>] credentials <tool> list|get|add|set|rename|remove|login
```

`project credentials` SHALL use the selected project overlay supplied by the `project` command group. It SHALL NOT expose `--project`, `--agent-def-dir`, or direct native-agent root selectors.

At minimum, the project credential family SHALL expose Houmao-owned tool lanes for:

- `claude`
- `codex`
- `gemini`

#### Scenario: Explicit project directory selects project credentials
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project --project-dir /repo credentials claude list`
- **THEN** the command manages credentials in `/repo/.houmao`
- **AND THEN** it does not require a top-level `credentials --project` wrapper

#### Scenario: Project credentials reject direct native target options
- **WHEN** an operator runs `houmao-mgr project credentials codex list --agent-def-dir /tmp/agents`
- **THEN** the command fails as an unsupported option
- **AND THEN** the diagnostic does not imply that project credentials can directly target native-agent roots

### Requirement: Direct native-agent credentials are internals-only when retained
Direct credential CRUD for a plain native-agent root, if retained, SHALL be exposed under the internal native-agent command family rather than as a public top-level command.

The retained internal shape SHALL be:

```text
houmao-mgr internals native-agent credentials <tool> list|get|add|set|rename|remove|login
```

The internal command SHALL use the native-agent root selection contract from `internals native-agent`, including explicit `--native-agent-root` or the maintained native-agent root environment selector.

#### Scenario: Direct native credentials use native-agent root
- **WHEN** `/tmp/native/tools/codex/auth/work/` exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent credentials codex list --native-agent-root /tmp/native`
- **THEN** the command lists direct Codex credentials under `/tmp/native/tools/codex/auth/`
- **AND THEN** it does not require a Houmao project overlay

## REMOVED Requirements

### Requirement: `houmao-mgr credentials` exposes a dedicated credential-management tree
**Reason**: The top-level credential family duplicates `project credentials` only to expose project target selection, and it multiplexes public project workflow with direct native-agent storage management.
**Migration**: Use `houmao-mgr project [--project-dir <dir>] credentials <tool> ...` for project credentials. Use `houmao-mgr internals native-agent credentials <tool> ... --native-agent-root <dir>` for retained direct native-agent credential CRUD.

### Requirement: `credentials` resolves one target backend before running actions
**Reason**: Target multiplexing is removed from the public top-level credential family. Project target selection is owned by the `project` group, and direct native-agent selection is owned by `internals native-agent`.
**Migration**: Replace `houmao-mgr credentials --project <tool> ...` with `houmao-mgr project credentials <tool> ...`, and replace `houmao-mgr credentials --agent-def-dir <dir> <tool> ...` with `houmao-mgr internals native-agent credentials <tool> ... --native-agent-root <dir>`.

### Requirement: Direct agent-definition-dir credential actions manage named auth directories
**Reason**: Direct named auth-directory management remains useful only as native-agent internals, not as a top-level public workflow.
**Migration**: Use the retained internal native-agent credential command for plain native-agent roots.

### Requirement: Direct agent-definition-dir rename rewrites maintained in-tree auth references
**Reason**: Direct in-tree auth reference rewriting belongs to the retained internal native-agent credential command rather than the removed top-level target-variant family.
**Migration**: Use `houmao-mgr internals native-agent credentials <tool> rename --native-agent-root <dir> ...`.
