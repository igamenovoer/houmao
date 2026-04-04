## REMOVED Requirements

### Requirement: Affected demos launch against the current agent-definition model
**Reason**: The repository is archiving the current `scripts/demo/*` surface under `scripts/demo/legacy/` as historical reference rather than preserving those demo packs as maintained launch obligations.
**Migration**: Redesign replacement demos later and specify them as new supported capabilities instead of treating the archived demo set as current product surface.

### Requirement: Launch recovery scope is limited to startup success
**Reason**: This requirement still assumes the current demo and tutorial packs are maintained workflows that must be repaired.
**Migration**: When redesigned replacements exist, define their supported startup and post-start behavior explicitly in new capabilities rather than inheriting the archived demo-recovery contract.

### Requirement: Compatibility-only demo field names may remain temporarily
**Reason**: This requirement is only meaningful while current demo-owned config/state payloads remain part of the supported system contract.
**Migration**: Any surviving live non-demo compatibility fields should be specified by the capabilities that still own those surfaces after demo archival.
