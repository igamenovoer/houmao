## MODIFIED Requirements

### Requirement: `houmao-mgr project agents tools` mirrors the project-local tool tree
`houmao-mgr` SHALL expose a project-local tool administration subtree shaped as:

```text
houmao-mgr project agents tools <tool> get
houmao-mgr project agents tools <tool> setups <verb>
```

At minimum, `project agents tools` SHALL expose Houmao-owned tool families for:

- `claude`
- `codex`
- `gemini`

At minimum, each supported tool family SHALL expose:

- `get`
- `setups`

The help text for this subtree SHALL present it as management for project-local tool content under `.houmao/agents/tools/<tool>/`.

#### Scenario: Operator sees the project agents tools tree
- **WHEN** an operator runs `houmao-mgr project agents tools --help`
- **THEN** the help output lists the supported tool families
- **AND THEN** the help output presents `project agents tools` as management for `.houmao/agents/tools/`

#### Scenario: Operator sees the setup verbs for one tool
- **WHEN** an operator runs `houmao-mgr project agents tools claude --help`
- **THEN** the help output presents `get` and `setups`
- **AND THEN** those commands are described as operations on `.houmao/agents/tools/claude/`

## REMOVED Requirements

### Requirement: `project agents tools <tool> auth` manages catalog-backed auth profiles and derived auth projections
**Reason**: Credential CRUD moves to the separate `houmao-mgr credentials ...` and `houmao-mgr project credentials ...` command families so credentials are no longer owned by the tool-maintenance subtree.
**Migration**: Use `houmao-mgr project credentials <tool> list|get|add|set|rename|remove` for active project overlays, or `houmao-mgr credentials <tool> ... --agent-def-dir <path>` for plain agent-definition directories.

### Requirement: `project agents tools <tool> auth get` reports one auth profile safely and `auth set` uses patch semantics
**Reason**: Safe credential inspection and patch-style updates are now specified and implemented on the dedicated credential-management surface.
**Migration**: Use `houmao-mgr project credentials <tool> get|set ...` for project overlays or `houmao-mgr credentials <tool> get|set --agent-def-dir <path> ...` for plain agent-definition directories.

### Requirement: Gemini auth bundles support API key, optional endpoint override, and OAuth inputs
**Reason**: Gemini credential-lane requirements now belong to the dedicated credential-management capability instead of the project tool-maintenance subtree.
**Migration**: Use `houmao-mgr project credentials gemini ...` or `houmao-mgr credentials gemini ... --agent-def-dir <path>` for Gemini credential management.

### Requirement: Claude auth bundles support vendor OAuth token and imported login state
**Reason**: Claude credential-lane requirements now belong to the dedicated credential-management capability instead of the project tool-maintenance subtree.
**Migration**: Use `houmao-mgr project credentials claude ...` or `houmao-mgr credentials claude ... --agent-def-dir <path>` for Claude credential management.

### Requirement: `project agents tools <tool> auth rename` changes only the display name
**Reason**: Credential rename semantics are now owned by the dedicated credential-management capability, which distinguishes project-backed metadata rename from plain-directory rename with reference rewrites.
**Migration**: Use `houmao-mgr project credentials <tool> rename ...` for project overlays or `houmao-mgr credentials <tool> rename --agent-def-dir <path> ...` for plain agent-definition directories.
