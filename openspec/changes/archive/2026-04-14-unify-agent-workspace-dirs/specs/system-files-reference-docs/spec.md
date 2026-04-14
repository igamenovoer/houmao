## ADDED Requirements

### Requirement: System-files reference documents managed workspace lanes
System-files reference documentation SHALL describe the per-agent workspace envelope, its `houmao-memo.md` file, and its scratch and persist lanes.

The documentation SHALL explain that `HOUMAO_AGENT_SCRATCH_DIR` replaces the old `job_dir` scratch role and that `HOUMAO_AGENT_PERSIST_DIR` replaces the old durable memory role when persistence is enabled.

The documentation SHALL explain that `HOUMAO_AGENT_MEMO_FILE` points to the per-agent memo file used for live-agent rules and loop initialization material.

The documentation SHALL not present `.houmao/jobs/<session-id>/`, `HOUMAO_JOB_DIR`, or `HOUMAO_MEMORY_DIR` as current managed-agent contracts.

#### Scenario: Reference reader understands the new workspace layout
- **WHEN** an operator reads the system-files reference
- **THEN** the reference shows `<active-overlay>/memory/agents/<agent-id>/scratch/`
- **AND THEN** the reference shows `<active-overlay>/memory/agents/<agent-id>/persist/`
- **AND THEN** the reference shows `<active-overlay>/memory/agents/<agent-id>/houmao-memo.md`
- **AND THEN** the reference explains the scratch and persist lifetime difference
