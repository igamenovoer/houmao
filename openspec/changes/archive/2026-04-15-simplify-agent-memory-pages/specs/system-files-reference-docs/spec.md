## REMOVED Requirements

### Requirement: System-files reference documents managed workspace lanes
**Reason**: The system-files reference must no longer describe managed-agent memory as scratch and persist workspace lanes.

**Migration**: Document managed memory as `houmao-memo.md` plus indexed `pages/`.

## ADDED Requirements

### Requirement: System-files reference documents managed memory pages
System-files reference documentation SHALL describe the per-agent memory root, its `houmao-memo.md` file, and its `pages/` directory.

The documentation SHALL explain that `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR` are the current managed-agent memory environment variables.

The documentation SHALL explain that managed memory pages are for small operator-visible notes, instructions, and durable context, not generic scratch files, generated artifacts, provider-owned internal memory, or shared external persist directories.

The documentation SHALL not present `.houmao/jobs/<session-id>/`, `HOUMAO_JOB_DIR`, `HOUMAO_MEMORY_DIR`, `HOUMAO_AGENT_SCRATCH_DIR`, or `HOUMAO_AGENT_PERSIST_DIR` as current managed-agent memory contracts.

#### Scenario: Reference reader understands the simplified memory layout
- **WHEN** an operator reads the system-files reference
- **THEN** the reference shows `<active-overlay>/memory/agents/<agent-id>/houmao-memo.md`
- **AND THEN** the reference shows `<active-overlay>/memory/agents/<agent-id>/pages/`
- **AND THEN** the reference explains that `houmao-memo.md` indexes page content
- **AND THEN** the reference does not show scratch or persist lanes as current memory layout
