## ADDED Requirements

### Requirement: `project easy instance launch` exposes gateway TUI tracking timings for auto-attach
`houmao-mgr project easy instance launch` SHALL accept optional one-shot gateway TUI tracking timing overrides for launch-time gateway auto-attach.

The launch surface SHALL expose the timing overrides as:

- `--gateway-tui-watch-poll-interval-seconds`
- `--gateway-tui-stability-threshold-seconds`
- `--gateway-tui-completion-stability-seconds`
- `--gateway-tui-unknown-to-stalled-timeout-seconds`
- `--gateway-tui-stale-active-recovery-seconds`

When launch-time gateway auto-attach is enabled, the command SHALL pass any supplied gateway TUI timing overrides to the delegated managed-agent launch and gateway attach path.

When `--no-gateway` is supplied, the command SHALL reject any gateway TUI timing override because no launch-time gateway attach will be requested.

Supplying gateway TUI timing overrides SHALL NOT rewrite the stored specialist or easy-profile launch defaults.

#### Scenario: Easy launch passes timing overrides to gateway auto-attach
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --gateway-tui-completion-stability-seconds 2.5`
- **AND WHEN** launch-time gateway auto-attach is enabled
- **THEN** the delegated managed-agent launch receives a gateway TUI tracking timing override for completion stability of `2.5` seconds
- **AND THEN** the attached gateway uses that override for gateway-owned TUI tracking

#### Scenario: Easy launch timing override does not mutate profile defaults
- **WHEN** an operator launches from easy profile `alice` with one or more `--gateway-tui-*` timing overrides
- **THEN** the launch uses those timing overrides for that launch-time gateway attach
- **AND THEN** the stored easy profile remains unchanged

#### Scenario: Easy launch rejects timing overrides when gateway attach is disabled
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --no-gateway --gateway-tui-stale-active-recovery-seconds 10`
- **THEN** the command fails before launch
- **AND THEN** the error states that gateway TUI timing overrides require launch-time gateway attach
