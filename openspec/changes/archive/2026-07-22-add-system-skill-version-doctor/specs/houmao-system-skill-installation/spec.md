## ADDED Requirements

### Requirement: Lifecycle operations do not enforce skill release metadata
System-skill install, sync, upgrade, status, uninstall, managed launch, rebuild, relaunch, join, prompt generation, and skill invocation SHALL NOT require or compare installed `houmao_version` values.

Copy projection SHALL preserve the checked-in frontmatter bytes. Symlink projection SHALL expose the checked-in source unchanged. Existing manifest, receipt, digest, ownership, policy, and transaction rules SHALL remain authoritative for those lifecycle operations.

#### Scenario: Existing installation has no version field
- **WHEN** a lifecycle operation encounters a previously installed root without `houmao_version`
- **THEN** it applies its existing receipt, content, ownership, and conflict rules
- **AND THEN** it does not fail solely because version metadata is missing

#### Scenario: Installed version differs from running Houmao
- **WHEN** managed launch or synchronization encounters a version mismatch
- **THEN** version equality does not become a lifecycle precondition
- **AND THEN** only an explicit doctor invocation reports the mismatch as version evidence

### Requirement: Version metadata does not change lifecycle schemas
The v4 system-skill manifest and v2 receipt schemas SHALL remain unchanged. Receipts SHALL continue recording lifecycle package version and complete-tree digests without adding a required per-skill version field.

Doctor SHALL NOT migrate or rewrite receipts when reading installed frontmatter.

#### Scenario: Current pack is installed after metadata is added
- **WHEN** install projects a versioned standalone root
- **THEN** its existing tree digest naturally covers the frontmatter bytes
- **AND THEN** the receipt remains valid under `houmao-system-skills-receipt.v2`

#### Scenario: Doctor reads a current receipt
- **WHEN** doctor examines a lifecycle-managed home
- **THEN** it leaves the receipt bytes unchanged
- **AND THEN** it reads observed skill versions from installed `SKILL.md` files
