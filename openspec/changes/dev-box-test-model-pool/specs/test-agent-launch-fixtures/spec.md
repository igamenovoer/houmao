# Spec Delta

## ADDED Requirements

### Requirement: Manager fixture preparation applies birth-time reasoning levels across supported clients
When preparing a `--surface manager` fixture run with an explicit `--reasoning-level` (from CLI flags or a selected model-pool entry), the helper SHALL validate the non-negative preset index against the selected client's declared reasoning slots (including DSH `dsh_reasoning` slot mappings and Kimi `support_efforts`) and SHALL record that `reasoning_level` on the generated `fixture-agent` launch profile before launch.

#### Scenario: DSH manager preparation pins xhigh reasoning without post-prepare CLI calls
- **WHEN** a developer prepares a manager-surface DSH fixture with `dsh_reasoning` declaring `off`, `low`, `medium`, and `xhigh` and `--reasoning-level 3`
- **THEN** preparation creates the `fixture-agent` project profile with `reasoning_level = 3` before launch without requiring a separate `houmao-mgr project profile set` command

#### Scenario: Out-of-range reasoning level fails before creating run state
- **WHEN** a manager-surface fixture specifies a `--reasoning-level` exceeding the selected model's declared reasoning slots or on a model with `dsh_reasoning = false`
- **THEN** validation fails with an actionable range error before allocating a run directory

### Requirement: Fixture preparation accepts model-pool entries interchangeably with explicit case flags
`fixture.py check` and `fixture.py prepare` SHALL translate a selected `model-pool.toml` entry into the same `ResolvedConfig`, isolated client home, and credential projection used by direct `--case` or `--auth-method native-login` invocations, preserving identical raw, manager, and passive-server runtime behavior.

#### Scenario: Pool-backed self-hosted preparation matches explicit flag preparation
- **WHEN** a developer prepares two manager runs with identical self-hosted DSH settings, one via explicit flags and one via `--pool-key`
- **THEN** both runs generate equivalent `tool-params.yaml`, specialist, and launch-profile projections while keeping distinct run directories
