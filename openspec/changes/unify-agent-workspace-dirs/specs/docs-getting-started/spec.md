## ADDED Requirements

### Requirement: Getting-started docs explain managed workspace scratch and persist lanes
Getting-started documentation SHALL explain the default managed-agent workspace layout, the `houmao-memo.md` file, the scratch lane, the optional persist lane, and the new environment variables.

The docs SHALL show `--persist-dir` and `--no-persist-dir` examples instead of `--memory-dir` and `--no-memory-dir`.

The docs SHALL direct temporary ledgers and outputs to `HOUMAO_AGENT_SCRATCH_DIR` and durable notes to `HOUMAO_AGENT_PERSIST_DIR` when persistence is enabled.

The docs SHALL direct live-agent initialization rules and task-handling notes to `HOUMAO_AGENT_MEMO_FILE`.

#### Scenario: New user sees persist-dir launch examples
- **WHEN** a new user reads the managed workspace getting-started page
- **THEN** the page shows a default launch example
- **AND THEN** it shows an explicit `--persist-dir` example
- **AND THEN** it shows a `--no-persist-dir` example
- **AND THEN** it explains the `houmao-memo.md` memo file
- **AND THEN** it does not show `--memory-dir` as the current option
