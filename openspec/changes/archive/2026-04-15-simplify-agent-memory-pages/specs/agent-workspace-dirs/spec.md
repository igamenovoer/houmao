## REMOVED Requirements

### Requirement: Managed agents expose one workspace envelope with scratch and persist lanes
**Reason**: The managed-agent memory subsystem is no longer a generic workspace envelope. Houmao now owns only a memo-pages memory directory with `houmao-memo.md` and `pages/`.

**Migration**: Use the `agent-memory-pages` capability. Store task artifacts in the launched workdir or an explicit project path, and store small durable notes as memory pages.

### Requirement: Managed agent workspace environment variables use lane names
**Reason**: Lane-oriented environment variables are removed with the scratch/persist model.

**Migration**: Use `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR`.

### Requirement: Workspace file operations are lane-scoped and path-contained
**Reason**: Supported file operations now address pages under `pages/` only, not arbitrary scratch or persist lanes.

**Migration**: Use memory page operations. Paths remain relative and contained under the managed pages directory.

### Requirement: Houmao exposes supported workspace operations through CLI and gateway surfaces
**Reason**: The public workspace surface is replaced by memo/page operations.

**Migration**: Use the supported memory path, memo, page, and reindex operations on CLI, gateway, and pair-server surfaces.
