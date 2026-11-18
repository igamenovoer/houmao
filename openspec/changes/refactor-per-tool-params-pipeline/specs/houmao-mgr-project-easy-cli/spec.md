# houmao-mgr-project-easy-cli Specification

## ADDED Requirements

### Requirement: `project` surfaces support per-tool parameters for specialists and project profiles

`houmao-mgr project specialist create|set` and `houmao-mgr project profile create|set` SHALL accept `--tool-params <json-or-@path>` (JSON or `@<yaml-or-json-file>`) to persist validated partial `tool_params` for the resolved tool, and `set` SHALL also accept `--clear-tool-params` to remove stored `tool_params`. `specialist get` and `profile get` SHALL report stored `tool_params` as secret-free structured metadata and refresh compatibility projections accordingly.

#### Scenario: Specialist create accepts file-referenced YAML tool_params
- **WHEN** an operator runs `houmao-mgr project specialist create --name qwen-dsh --tool dsh --credential local --tool-params @dsh-params.yaml`
- **THEN** the command validates `dsh-params.yaml` against the DSH partial `tool_params` schema, persists it in the specialist's catalog preset, and projects `tool_params` into `.houmao/agents/presets/`

#### Scenario: Profile set patches and clears stored tool_params
- **WHEN** an operator runs `houmao-mgr project profile set --name b1 --tool-params '{"mcp_servers":[]}'` and later runs `houmao-mgr project profile set --name b1 --clear-tool-params`
- **THEN** the first command merges the partial `tool_params` into `b1` and refreshes `.houmao/agents/launch-profiles/b1.yaml`
- **AND THEN** `--clear-tool-params` removes profile-owned `tool_params` so future launches inherit lower layers
