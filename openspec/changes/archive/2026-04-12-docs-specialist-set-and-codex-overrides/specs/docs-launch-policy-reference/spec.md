## MODIFIED Requirements

### Requirement: Launch policy reference page exists

The Codex hooks table in `docs/reference/build-phase/launch-policy.md` SHALL include a row for `codex.append_unattended_cli_overrides`. That row SHALL describe the hook as appending final Codex CLI `-c` override arguments for unattended-owned surfaces (`approval_policy`, `sandbox_mode`, `notice.hide_full_access_warning`) so project-local `config.toml` cannot weaken the strategy-owned unattended posture.

#### Scenario: Reader sees the Codex CLI override hook in the launch policy reference

- **WHEN** a reader opens the Codex hooks table in the launch policy reference
- **THEN** the table includes a `codex.append_unattended_cli_overrides` row
- **AND THEN** the row explains that the hook appends CLI `-c` overrides to prevent project-local config from weakening unattended posture
