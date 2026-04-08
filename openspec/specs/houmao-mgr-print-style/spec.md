# houmao-mgr-print-style Specification

## Purpose
Define print-style selection and structured-output rendering for `houmao-mgr`.

## Requirements
### Requirement: `houmao-mgr` supports three print styles — plain, json, and fancy
`houmao-mgr` SHALL support three mutually exclusive print styles that control how command output is formatted:

- `plain`: Human-readable aligned text using `click.echo()` only. This is the default.
- `json`: Machine-readable JSON with 2-space indent and sorted keys.
- `fancy`: Rich-formatted output using the `rich` library with tables, panels, and colored status indicators.

Each command that produces structured output SHALL respect the active print style.

#### Scenario: Default output is plain text
- **WHEN** an operator runs `houmao-mgr agents list` without any print style flag or env var
- **THEN** the output is human-readable aligned text
- **AND THEN** the output does NOT contain JSON braces or raw JSON formatting

#### Scenario: JSON output uses stable machine-readable formatting
- **WHEN** an operator runs `houmao-mgr agents list --print-json`
- **THEN** the output is valid JSON with 2-space indent and sorted keys
- **AND THEN** the output is identical in structure to the command's structured payload

#### Scenario: Fancy output uses rich formatting
- **WHEN** an operator runs `houmao-mgr agents list --print-fancy` in a TTY terminal
- **THEN** the output includes rich table formatting with borders and alignment

### Requirement: Print style is selected via `--print-plain`, `--print-json`, or `--print-fancy` flags on the root group
The `houmao-mgr` root click group SHALL accept three mutually exclusive flag-value options: `--print-plain`, `--print-json`, and `--print-fancy`. These flags SHALL map to a single `print_style` parameter.

Only one flag MAY be provided per invocation. If more than one is provided, Click's flag-value mechanics SHALL resolve to the last one specified.

The flags SHALL be visible in `houmao-mgr --help` output.

#### Scenario: Flags appear in root help
- **WHEN** an operator runs `houmao-mgr --help`
- **THEN** the help output lists `--print-plain`, `--print-json`, and `--print-fancy` as options

#### Scenario: Flag controls output of a subcommand
- **WHEN** an operator runs `houmao-mgr --print-json server status`
- **THEN** the `server status` output is JSON-formatted

#### Scenario: Flag works when placed after the subcommand
- **WHEN** an operator runs `houmao-mgr server status --print-json`
- **THEN** the `server status` output is JSON-formatted
- **AND THEN** the behavior is identical to placing the flag before the subcommand

### Requirement: `HOUMAO_CLI_PRINT_STYLE` env var provides persistent print style preference
`houmao-mgr` SHALL read the `HOUMAO_CLI_PRINT_STYLE` environment variable to resolve a persistent print style preference. Valid values SHALL be `plain`, `json`, and `fancy` (case-insensitive).

Explicit CLI flags SHALL override the env var. The env var SHALL override the default (`plain`).

If the env var contains an unrecognized value, `houmao-mgr` SHALL ignore it and fall back to the default `plain` style.

#### Scenario: Env var selects JSON style
- **WHEN** `HOUMAO_CLI_PRINT_STYLE=json` is set
- **AND WHEN** an operator runs `houmao-mgr agents list` without any `--print-*` flag
- **THEN** the output is JSON-formatted

#### Scenario: Explicit flag overrides env var
- **WHEN** `HOUMAO_CLI_PRINT_STYLE=json` is set
- **AND WHEN** an operator runs `houmao-mgr --print-plain agents list`
- **THEN** the output is plain text, not JSON

#### Scenario: Invalid env var value falls back to default
- **WHEN** `HOUMAO_CLI_PRINT_STYLE=xml` is set
- **AND WHEN** an operator runs `houmao-mgr agents list` without any `--print-*` flag
- **THEN** the output is plain text (the default)

### Requirement: Output engine provides generic fallback renderers for all payload shapes
The output engine SHALL provide generic fallback renderers for `plain` and `fancy` modes so that every command produces correct output in all three styles without requiring a curated per-command renderer.

The `json` fallback SHALL serialize the payload with `json.dumps(indent=2, sort_keys=True)`.

The `plain` fallback SHALL render flat dicts as aligned `key: value` lines and list-bearing dicts as a header line followed by column-aligned rows.

The `fancy` fallback SHALL render flat dicts as a `rich.Table` with key-value columns and list-bearing dicts as a `rich.Table` with auto-detected column headers.

Pydantic `BaseModel` instances SHALL be normalized via `.model_dump(mode="json")` before rendering in all modes.

#### Scenario: Unknown payload shape renders without error in plain mode
- **WHEN** a command emits a deeply nested dict payload
- **AND WHEN** the active print style is `plain`
- **THEN** the output renders the top-level keys as aligned `key: value` lines without raising an exception

#### Scenario: Pydantic model renders correctly in all modes
- **WHEN** a command emits a Pydantic `BaseModel` instance
- **THEN** the model is serialized via `.model_dump(mode="json")` before rendering
- **AND THEN** the output is correct in `plain`, `json`, and `fancy` modes

### Requirement: Plain mode does not import `rich`
When the active print style is `plain`, the output engine SHALL NOT import the `rich` library. The `rich.Console` instance SHALL be created lazily only when `fancy` mode is active.

#### Scenario: Plain mode startup does not load rich
- **WHEN** the active print style is `plain`
- **AND WHEN** a command produces output
- **THEN** the `rich` module is NOT imported during that invocation

### Requirement: `emit()` is the central output function
`emit()` SHALL be the primary output dispatch point. `emit()` SHALL accept a payload and optional `plain_renderer` and `fancy_renderer` callables for curated output.

Before `emit()` dispatches to a generic renderer or a curated renderer, it SHALL normalize the payload to the renderer contract. When the payload is a Pydantic `BaseModel`, `emit()` SHALL serialize it via `.model_dump(mode="json")` and SHALL pass the normalized mapping or sequence payload to the selected renderer instead of the raw model instance.

When a curated renderer is provided and the active style matches, `emit()` SHALL call that renderer instead of the generic fallback using the normalized payload.

#### Scenario: emit() with no curated renderer uses generic fallback
- **WHEN** `emit(payload)` is called without curated renderers
- **AND WHEN** the active print style is `plain`
- **THEN** the generic plain fallback renders the normalized payload

#### Scenario: emit() with curated renderer uses it when style matches
- **WHEN** `emit(payload, plain_renderer=my_renderer)` is called
- **AND WHEN** the active print style is `plain`
- **THEN** `my_renderer` is called instead of the generic fallback
- **AND THEN** `my_renderer` receives the normalized payload shape rather than the raw model instance

#### Scenario: curated renderer receives normalized Pydantic model payload
- **WHEN** a command emits a Pydantic `BaseModel` payload
- **AND WHEN** `emit(payload, plain_renderer=my_renderer)` is called
- **AND WHEN** the active print style is `plain`
- **THEN** `my_renderer` receives the `.model_dump(mode="json")` result
- **AND THEN** the command does not print an empty placeholder solely because the curated renderer expected a mapping

#### Scenario: managed-agent list renders populated human-oriented output from model payload
- **WHEN** `houmao-mgr agents list` emits a populated Pydantic model payload
- **AND WHEN** the active print style is `plain`
- **THEN** the curated renderer receives a normalized mapping containing the `agents` collection
- **AND THEN** the command renders managed-agent rows instead of `No managed agents.`

#### Scenario: gateway status renders populated human-oriented output from model payload
- **WHEN** `houmao-mgr agents gateway status` emits a populated Pydantic model payload
- **AND WHEN** the active print style is `plain`
- **THEN** the curated renderer receives a normalized mapping containing the gateway status fields
- **AND THEN** the command renders gateway details instead of `(no gateway status)`
