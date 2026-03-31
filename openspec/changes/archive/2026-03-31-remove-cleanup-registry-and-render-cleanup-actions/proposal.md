## Why

`houmao-mgr` cleanup has two operator-facing problems today: the legacy `admin cleanup-registry` alias keeps the cleanup surface split across two spellings, and plain cleanup output hides the actual artifact actions behind counts and placeholders. That makes the CLI noisier than necessary and forces operators to switch to JSON just to see what would be or was cleaned.

## What Changes

- Remove the native `houmao-mgr admin cleanup-registry` compatibility alias and standardize on the grouped `houmao-mgr admin cleanup registry` path.
- Render cleanup results in human-oriented output as per-artifact lines for planned, applied, blocked, and preserved actions instead of only showing summary counts.
- Preserve the existing structured cleanup payload shape for JSON consumers while improving the plain and fancy operator views.
- Update cleanup help, tests, and reference docs to remove the retired alias and describe the new cleanup output behavior.
- **BREAKING**: `houmao-mgr admin cleanup-registry` is no longer a supported native command path.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `houmao-srv-ctrl-native-cli`: retire the native `admin cleanup-registry` alias and make the grouped `admin cleanup` tree the only supported cleanup command path.
- `houmao-mgr-cleanup-cli`: require human-oriented cleanup rendering to print each cleanup action line by line while preserving the existing structured JSON contract.
- `registry-reference-docs`: update registry cleanup operational guidance to use the grouped cleanup command and explain actionable cleanup result reporting.

## Impact

- Affected code:
  - `src/houmao/srv_ctrl/commands/admin.py`
  - `src/houmao/srv_ctrl/commands/agents/cleanup.py`
  - `src/houmao/srv_ctrl/commands/mailbox.py`
  - `src/houmao/srv_ctrl/commands/project.py`
  - `src/houmao/srv_ctrl/commands/output.py`
  - cleanup payload and renderer support modules
- Affected tests:
  - cleanup command help and behavior tests
  - output rendering tests
- Affected docs:
  - `docs/reference/cli/*.md`
  - `docs/reference/registry/operations/discovery-and-cleanup.md`
