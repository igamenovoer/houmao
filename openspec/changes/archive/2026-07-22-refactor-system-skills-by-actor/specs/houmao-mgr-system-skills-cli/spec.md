## ADDED Requirements

### Requirement: System-skills CLI exposes pack lifecycle commands
`houmao-mgr system-skills` SHALL expose `list`, `install`, `status`, `upgrade`, and `uninstall` for Houmao system-skill packs.

The command group SHALL manage public pack projections and receipts. It SHALL NOT expose protected routines or managed auto skills as independent install units.

#### Scenario: Operator opens system-skills help
- **WHEN** an operator runs `houmao-mgr system-skills --help`
- **THEN** help lists the five pack lifecycle commands
- **AND THEN** it describes protected routines as entrypoint-owned implementation rather than install selectors

### Requirement: System-skills list reports packs, public roles, and protected eligibility
`houmao-mgr system-skills list` SHALL report the `admin` and `agent` packs, their default lanes, public members and roles, and protected logical routines eligible for each entrypoint.

Plain output SHALL distinguish public names from protected logical ids. Structured output SHALL provide separate `packs`, `public_skills`, and `protected_routines` fields.

#### Scenario: Operator lists available packs
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the output identifies the two-public-skill admin pack and one-public-skill agent pack
- **AND THEN** no protected logical id is labeled independently installable

### Requirement: System-skills install selects complete packs
`houmao-mgr system-skills install` SHALL accept a repeatable `--pack admin|agent` option plus the supported tool, home, and projection-mode options.

When `--pack` is omitted for an external home, the command SHALL select `admin`. Unknown packs and obsolete `--set` or `--skill` selection SHALL fail with a migration-oriented diagnostic.

#### Scenario: Default external install selects admin
- **WHEN** an operator runs install without `--pack`
- **THEN** the command installs `houmao-admin-welcome` and `houmao-admin-entrypoint` atomically
- **AND THEN** plain and structured output report both public paths and the `admin` pack id

#### Scenario: Obsolete low-level selector is used
- **WHEN** an operator attempts `--skill houmao-agent-inspect`
- **THEN** the command rejects the removed selector
- **AND THEN** it explains that protected inspect work is invoked through a public entrypoint

### Requirement: System-skills status and upgrade use receipt evidence
`houmao-mgr system-skills status` SHALL report each pack as absent, complete, incomplete, drifted, or conflicting and SHALL report receipt version, public paths, projection mode, and legacy conflicts.

`houmao-mgr system-skills upgrade` SHALL stage and validate selected replacement packs, migrate only safely classified legacy paths, and commit transactionally.

#### Scenario: Status finds missing admin welcome
- **WHEN** the receipt owns the admin pack but the welcome path is absent
- **THEN** status reports the admin pack as incomplete
- **AND THEN** it identifies the missing welcome role

#### Scenario: Upgrade finds modified legacy path
- **WHEN** upgrade finds an old reserved path with unknown content
- **THEN** it reports a conflict and preserves that path
- **AND THEN** it does not partially commit the selected replacement pack

### Requirement: System-skills uninstall removes selected receipt-owned packs
`houmao-mgr system-skills uninstall` SHALL accept repeatable pack selection and SHALL remove every public member and materialization owned for each selected pack as one transaction.

It SHALL preserve unrelated skills, untracked public-name collisions, and ambiguous legacy paths. Output SHALL distinguish removed, absent, drifted, and preserved conflicting paths.

#### Scenario: Operator uninstalls admin pack
- **WHEN** the receipt owns a healthy admin pack and the operator selects `--pack admin`
- **THEN** uninstall removes both admin public siblings and the receipt-owned admin materialization
- **AND THEN** it leaves an independently owned agent pack unchanged

### Requirement: System-skills CLI retains supported target and output behavior
Pack lifecycle commands SHALL retain effective-home resolution, explicit tool-home overrides, plain output, and root `--print-json` structured output for Claude, Codex, Copilot, Kimi, and universal targets.

The CLI SHALL NOT claim Gemini system-skill support. Path output SHALL report public projection paths and SHALL report protected paths only as nested inspection detail.

#### Scenario: Structured Codex install output is requested
- **WHEN** an operator runs root `--print-json` with a Codex admin-pack install
- **THEN** output reports the resolved home, `admin` pack, both public projected paths, receipt path, and projection mode
- **AND THEN** it does not report each protected routine as a top-level installed skill

## REMOVED Requirements

### Requirement: `houmao-mgr system-skills` exposes the current Houmao-owned skill installation surface
**Reason**: The peer-skill installation surface is replaced by pack lifecycle management.
**Migration**: Use `list`, `install`, `status`, `upgrade`, and `uninstall` with pack selectors.

### Requirement: `houmao-mgr system-skills list` reports the current installable Houmao-owned skill inventory and named sets
**Reason**: Named sets and independently installable low-level skills are removed.
**Migration**: Read pack, public-role, and protected-eligibility output.

### Requirement: `houmao-mgr system-skills install` targets an explicit tool home and set-based selection
**Reason**: Set-based selection is removed.
**Migration**: Keep tool and home selection and replace sets with repeatable `--pack`.

### Requirement: `houmao-mgr system-skills` surfaces the renamed AG-UI interop skill
**Reason**: AG-UI interop is a protected routine.
**Migration**: Inspect its eligibility in `list` and invoke it through an entrypoint.

### Requirement: `houmao-mgr system-skills` surfaces the renamed specialist-management skill in current inventory
**Reason**: The compatibility specialist wrapper is removed.
**Migration**: Use the protected agent-definition route through the admin entrypoint.

### Requirement: `houmao-mgr system-skills` surfaces the user-control project-management skill
**Reason**: Project management is protected admin content, not an install unit.
**Migration**: Use the admin entrypoint project route.

### Requirement: `houmao-mgr system-skills` surfaces the user-control named set and credential-management skill
**Reason**: User-control sets are removed and credential management is admin-only protected content.
**Migration**: Install the admin pack and invoke its credential route.

### Requirement: `houmao-mgr system-skills` surfaces the user-control agent-definition skill
**Reason**: Agent definition is a protected admin routine.
**Migration**: Install the admin pack and invoke its agent-definition route.

### Requirement: `houmao-mgr system-skills` surfaces the packaged agent-instance lifecycle skill and updated CLI-default selection
**Reason**: Agent-instance is a protected shared routine and CLI default now selects a pack.
**Migration**: Use the appropriate public entrypoint.

### Requirement: `houmao-mgr system-skills` surfaces the unified mailbox skill inventory
**Reason**: Mailbox routines are protected agent or shared routes.
**Migration**: Inspect their audience eligibility and invoke them through an entrypoint.

### Requirement: `houmao-mgr system-skills` surfaces the packaged advanced-usage skill
**Reason**: Advanced usage is a protected shared routine.
**Migration**: Invoke the route through an eligible entrypoint.

### Requirement: `houmao-mgr system-skills` surfaces the packaged `houmao-touring` skill and touring set
**Reason**: Touring and its set are retired.
**Migration**: Use `houmao-admin-welcome` from the admin pack.

### Requirement: `houmao-mgr system-skills` surfaces the packaged `houmao-agent-inspect` skill and named set
**Reason**: Inspect is protected and no inspect set remains.
**Migration**: Invoke the inspect route through an eligible entrypoint.

### Requirement: `houmao-mgr system-skills` surfaces both packaged pairwise skill variants
**Reason**: Historical pairwise variants are retired.
**Migration**: Use maintained pro or lite protected routes.

### Requirement: `houmao-mgr system-skills` surfaces the packaged generic loop planner
**Reason**: Historical generic planner inventory is no longer public.
**Migration**: Use maintained pro or lite protected routes.

### Requirement: `houmao-mgr system-skills` surfaces managed-memory guidance
**Reason**: Memory is a protected shared routine.
**Migration**: Use the memory route through an eligible entrypoint.

### Requirement: `houmao-mgr system-skills` supports Copilot homes
**Reason**: Tool support now applies to pack lifecycle rather than peer-skill lifecycle.
**Migration**: Use the consolidated supported-target requirement in this delta.

### Requirement: `houmao-mgr system-skills status` discovers current projected skills from the filesystem
**Reason**: Receipt evidence and pack integrity replace stateless per-skill discovery.
**Migration**: Use pack-aware status; legacy paths appear as migration evidence.

### Requirement: `houmao-mgr system-skills uninstall` removes all known Houmao-owned skills from resolved homes
**Reason**: Global name-based deletion is unsafe and incompatible with pack ownership.
**Migration**: Uninstall selected receipt-owned packs.

### Requirement: `houmao-mgr system-skills` surfaces utility skills through all
**Reason**: The `all` set is removed.
**Migration**: Utilities appear as protected routes in their eligible packs.

### Requirement: `houmao-mgr system-skills install` plain output reports projected skill locations
**Reason**: Per-skill output is replaced by pack and public-role output.
**Migration**: Read the reported public paths and receipt location.

### Requirement: `houmao-mgr system-skills status` plain output reports projected skill paths
**Reason**: Status now reports pack integrity and public paths.
**Migration**: Use the pack-aware status output.

### Requirement: `houmao-mgr system-skills uninstall` plain output reports removed projected paths
**Reason**: Uninstall output must distinguish complete pack removal and preserved conflicts.
**Migration**: Use the pack-aware uninstall output.

### Requirement: System-skills CLI reports unified agent-definition ownership
**Reason**: Canonical ownership is protected routine metadata rather than a public inventory row.
**Migration**: Inspect protected route metadata or use admin-entrypoint help.

### Requirement: `houmao-mgr system-skills` surfaces pro as the current loop skill
**Reason**: Pro is protected and lite also remains maintained.
**Migration**: Invoke the desired loop route through an eligible entrypoint.

### Requirement: `houmao-mgr system-skills status` reports retired loop leftovers
**Reason**: Retired leftovers are generalized as legacy migration evidence.
**Migration**: Use pack status and upgrade conflict reporting.

### Requirement: `houmao-mgr system-skills install` reports retired cleanup
**Reason**: Fresh install does not silently clean untracked legacy content.
**Migration**: Use `upgrade` for classified legacy migration.

### Requirement: `houmao-mgr system-skills` rejects the removed LLM Wiki selector
**Reason**: All low-level skill selectors are removed, so a dedicated selector rule is redundant.
**Migration**: Select only `admin` or `agent` packs.

### Requirement: `houmao-mgr system-skills` supports Kimi projection without overstating discovery
**Reason**: Kimi support now applies to public pack projection.
**Migration**: Use the consolidated supported-target requirement.

### Requirement: `houmao-mgr system-skills` supports the universal install target
**Reason**: Universal support now applies to public pack projection.
**Migration**: Use the consolidated supported-target requirement.

### Requirement: `houmao-mgr system-skills` surfaces the graphing extension skill
**Reason**: Graphing is a protected shared routine and extensions are not install sets.
**Migration**: Invoke graphing through an eligible entrypoint.

### Requirement: System-skills CLI excludes Gemini targets
**Reason**: The consolidated supported-target requirement retains the exclusion without the old peer-skill model.
**Migration**: Use one of the documented supported targets.
