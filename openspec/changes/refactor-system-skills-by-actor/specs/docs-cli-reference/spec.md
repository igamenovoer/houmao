## ADDED Requirements

### Requirement: CLI reference documents system-skill pack lifecycle
`docs/reference/cli/system-skills.md` SHALL document `list`, `install`, `status`, `upgrade`, and `uninstall` with repeatable `--pack admin|agent`, supported tool and home resolution, copy and explicit symlink projection, plain output, and root `--print-json` output.

The reference SHALL explain CLI-default admin selection, managed-default agent selection, admin-pack atomicity, pack receipts, integrity states, and transaction rollback. It SHALL NOT document `--set` or low-level `--skill` as current selectors.

#### Scenario: Reader looks up external installation
- **WHEN** a reader opens the system-skills CLI reference
- **THEN** they find a complete admin-pack install example and effective-home rules
- **AND THEN** they understand that omission selects the admin pack

### Requirement: CLI reference documents public roles and actor entrypoints
The reference SHALL list `houmao-admin-welcome`, `houmao-admin-entrypoint`, and `houmao-agent-entrypoint` as the complete public surface.

It SHALL explain the welcome mutation boundary, admin explicit-target posture, agent self-identity verification, managed joined-session actor transition, and the absence of an agent welcome.

#### Scenario: Reader chooses between admin and agent entrypoints
- **WHEN** a reader needs to perform an operation from a human-operated home or managed home
- **THEN** the reference identifies the correct public entrypoint and actor semantics
- **AND THEN** it does not suggest that either actor can acquire the other actor's protected routes

### Requirement: CLI reference provides an entrypoint-qualified protected route map
The reference SHALL map every protected logical routine to eligible public entrypoints, route member names, major `houmao-mgr` command families, and actor-specific target behavior.

Protected designators SHALL be labeled as internal route traces. Copyable prompts SHALL begin with a public skill. The reference SHALL identify `houmao-touring` and `houmao-specialist-mgr` only in migration guidance.

#### Scenario: Reader finds credential-management commands
- **WHEN** a reader searches for credential-management skill guidance
- **THEN** the reference points to the admin entrypoint's protected credential route and maintained CLI families
- **AND THEN** it does not present `houmao-credential-mgr` as a top-level installed skill

### Requirement: CLI reference documents receipt-safe migration and removal
The reference SHALL explain status classifications, safe legacy digest or symlink detection, preserved modified conflicts, pack upgrade, receipt-owned uninstall, public projection paths, hidden symlink materialization, and host refresh requirements.

It SHALL state that fresh install does not silently delete old untracked flat paths and that an older Houmao release cannot safely mutate a new pack receipt.

#### Scenario: Reader has a modified legacy skill directory
- **WHEN** a reader follows migration guidance for an old home with modified flat content
- **THEN** the reference tells them that upgrade preserves and reports the conflict
- **AND THEN** it provides an explicit resolution path before retrying

### Requirement: CLI reference retains supported provider boundaries at pack level
The reference SHALL document pack projection for Claude, Codex, Copilot, Kimi, and universal targets, including maintained Kimi reachability caveats.

It SHALL state that Gemini is not a supported system-skill projection target and that `houmao-auto-system-prompt` remains separate from pack lifecycle commands.

#### Scenario: Reader checks Copilot or Gemini support
- **WHEN** a reader compares system-skill targets
- **THEN** Copilot is identified as a pack projection target rather than a launch backend
- **AND THEN** Gemini is not presented as a supported pack target

## REMOVED Requirements

### Requirement: System-skills reference documents the renamed specialist-management skill
**Reason**: The compatibility specialist skill is removed.
**Migration**: Document the admin entrypoint's protected agent-definition route.

### Requirement: System-skills reference documents the packaged `houmao-project-mgr` skill and its project-management boundary
**Reason**: Project management is an admin-only protected routine.
**Migration**: Put the boundary in the protected route map.

### Requirement: System-skills reference documents the packaged `houmao-mailbox-mgr` skill and its mailbox-admin boundary
**Reason**: Mailbox management is protected shared content.
**Migration**: Document both actor branches in the route map.

### Requirement: System-skills reference documents the packaged agent-instance lifecycle skill and its boundary
**Reason**: Agent-instance is a protected shared routine.
**Migration**: Document its admin and self branches under public entrypoints.

### Requirement: System-skills reference documents the packaged agent-messaging skill and its communication-path boundary
**Reason**: Agent messaging is a protected shared routine.
**Migration**: Document its entrypoint-qualified routes.

### Requirement: System-skills reference documents effective-home resolution and omitted-selection defaults
**Reason**: Omitted selection now chooses an audience pack instead of fixed skill sets.
**Migration**: Document effective-home resolution with the admin pack default.

### Requirement: System-skills reference documents the packaged agent-gateway skill and its gateway-service boundary
**Reason**: Agent gateway is a protected shared routine.
**Migration**: Document its entrypoint-qualified routes and actor branches.

### Requirement: CLI reference for scoped `agents ... mail` reflects the unified email-comms skill boundary
**Reason**: Unified email comms is reached through the agent or admin entrypoint.
**Migration**: Describe the protected route and public invocation together with scoped mail commands.

### Requirement: System-skills reference documents both pairwise skill variants and their boundary
**Reason**: Historical pairwise variants are retired.
**Migration**: Document maintained pro and lite protected routes.

### Requirement: System-skills reference documents the generic loop planner replacement
**Reason**: Loop planners are no longer public peer skills.
**Migration**: Document entrypoint-qualified pro and lite routes.

### Requirement: System-skills reference documents Copilot support
**Reason**: Copilot support now applies to pack lifecycle.
**Migration**: Document it in the pack target section.

### Requirement: CLI reference documents system-skills uninstall
**Reason**: Per-skill uninstall is replaced by receipt-owned pack uninstall.
**Migration**: Document selected pack removal and preserved conflicts.

### Requirement: CLI reference explains system-skills home and projection output
**Reason**: Output now distinguishes public paths, nested protected detail, receipts, and materializations.
**Migration**: Use the pack projection and status output contract.

### Requirement: CLI reference describes unified agent-definition skill
**Reason**: Agent definition is a protected admin routine.
**Migration**: Document it in the protected route map.

### Requirement: CLI reference documents pro as current loop skill
**Reason**: Pro is protected and lite also remains maintained.
**Migration**: Document both routes and their intended use.

### Requirement: CLI reference documents retired cleanup when relevant
**Reason**: Unconditional cleanup is replaced by safe legacy classification during upgrade.
**Migration**: Document digest and symlink evidence, conflicts, and explicit resolution.

### Requirement: CLI reference includes lite in current system-skill inventory
**Reason**: Lite is no longer a public inventory row.
**Migration**: List it in the protected route map.

### Requirement: System-skills CLI reference distinguishes CLI management from installed-skill help
**Reason**: Help now differs across welcome, entrypoint, and protected route roles.
**Migration**: Explain pack management separately from role-appropriate public help.

### Requirement: System-skills CLI reference notes the external Skills CLI install path
**Reason**: Pack composition and receipts require the Houmao-owned installer as the authoritative path in this change.
**Migration**: Use `houmao-mgr system-skills install --pack admin` unless an external distributor explicitly supports the complete pack contract.

### Requirement: CLI reference omits the removed LLM Wiki utility system skill
**Reason**: The manifest defines the complete protected inventory without a dedicated exception.
**Migration**: List only manifest-declared routines.

### Requirement: CLI reference documents corrected Kimi system-skill and launch behavior
**Reason**: Kimi system-skill behavior now applies to public pack projection.
**Migration**: Keep launch and reachability caveats while replacing peer-skill paths with pack paths.

### Requirement: CLI reference documents the graphing extension skill
**Reason**: Graphing is protected shared content.
**Migration**: Document its entrypoint-qualified route.

### Requirement: CLI reference documents extensions set behavior
**Reason**: The extensions set is removed.
**Migration**: Explain graphing as a protected shared routine within actor packs.

### Requirement: CLI reference explains retired graphing utility cleanup
**Reason**: Retired cleanup is generalized as safe legacy migration.
**Migration**: Use the upgrade and conflict-handling section.

### Requirement: CLI reference documents no Gemini surface
**Reason**: Provider boundaries now apply to pack projection as a whole.
**Migration**: State supported and unsupported targets in one pack-level section.

