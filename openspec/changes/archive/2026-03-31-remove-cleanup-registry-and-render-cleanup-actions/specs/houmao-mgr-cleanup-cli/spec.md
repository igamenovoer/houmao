## ADDED Requirements

### Requirement: Human-oriented cleanup output lists per-artifact actions
Cleanup commands that emit the normalized cleanup payload SHALL render populated action buckets as per-artifact output in human-oriented print styles.

This requirement applies to cleanup command families that share the normalized cleanup payload shape, including:

- `houmao-mgr admin cleanup ...`
- `houmao-mgr agents cleanup ...`
- `houmao-mgr mailbox cleanup`
- `houmao-mgr project mailbox cleanup`

For `plain` and `fancy` print styles, each rendered action entry SHALL identify the artifact path and the cleanup reason, and it SHALL preserve enough context to distinguish artifact kind and any compact action details when present.

Human-oriented cleanup output SHALL NOT collapse populated action buckets into count-only placeholders when detailed action records are available.

`json` output SHALL continue to expose the structured cleanup payload with `planned_actions`, `applied_actions`, `blocked_actions`, `preserved_actions`, and `summary`.

#### Scenario: Plain dry-run output lists planned and preserved actions line by line
- **WHEN** an operator runs a supported cleanup command in `plain` mode with one or more `planned_actions` or `preserved_actions`
- **THEN** the output lists each action on its own line within the corresponding outcome bucket
- **AND THEN** the operator can see the artifact path and reason without switching to JSON

#### Scenario: Plain execute output lists applied and blocked actions line by line
- **WHEN** an operator runs a supported cleanup command in `plain` mode and the result contains one or more `applied_actions` or `blocked_actions`
- **THEN** the output lists each action on its own line within the corresponding outcome bucket
- **AND THEN** the output is not limited to summary counts alone

#### Scenario: JSON cleanup output remains structured
- **WHEN** an operator runs a supported cleanup command with `--print-json`
- **THEN** the output remains a structured JSON object containing the cleanup action arrays and summary fields
- **AND THEN** the command does not replace that machine-readable payload with renderer-specific plain-text lines
