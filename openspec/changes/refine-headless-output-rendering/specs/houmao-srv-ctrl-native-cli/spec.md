## ADDED Requirements

### Requirement: `houmao-mgr agents turn events` renders canonical headless events with a detail selector
`houmao-mgr agents turn events` SHALL render canonical Houmao semantic headless turn events rather than raw provider stdout lines.

The command SHALL support `--detail concise|detail` with default `concise`.

For default `concise` rendering, the command SHALL replay the same semantic summary used by the live bridge path: answer text as the primary body, concise action request/result lines, and provider-exposed completion or usage accounting when available.

The command SHALL continue to honor the active root print style:

- `plain`: human-readable text summaries of canonical events
- `json`: canonical semantic JSON output
- `fancy`: rich human-readable rendering of canonical events

`detail` mode SHALL expose the extra structured event detail defined by the canonical headless event model.

For `plain` and `fancy` styles, the command SHALL replay canonical events using the same headless-domain renderer core used by the live bridge path for the selected `style` and `detail`.

#### Scenario: Default event inspection is human-readable and concise
- **WHEN** an operator runs `houmao-mgr agents turn events <agent-ref> <turn-id>` without overriding detail or root print style
- **THEN** the command renders concise human-readable summaries of canonical headless events
- **AND THEN** it does not print raw provider JSON lines by default
- **AND THEN** that concise summary includes answer text plus any available action lifecycle and completion-accounting lines defined by the canonical headless renderer contract

#### Scenario: JSON detail inspection exposes canonical structured event detail
- **WHEN** an operator runs `houmao-mgr --print-json agents turn events <agent-ref> <turn-id> --detail detail`
- **THEN** the command prints canonical semantic JSON for that turn's events
- **AND THEN** the output includes the extra structured detail defined for detail mode rather than raw provider stdout passthrough

#### Scenario: Plain replay matches live plain rendering semantics
- **WHEN** an operator inspects a turn whose live pane used `style=plain` and `detail=concise`
- **THEN** `houmao-mgr agents turn events` renders the same semantic summaries for assistant, tool, and completion events
- **AND THEN** any differences are limited to CLI transport framing rather than different event wording rules

#### Scenario: Replay reuses bridge renderer logic without owning the live process
- **WHEN** an operator replays one managed headless turn through `houmao-mgr agents turn events`
- **THEN** the command uses the same headless-domain renderer core as the live bridge path
- **AND THEN** it does so by replaying canonical events rather than by taking ownership of the provider subprocess used during live execution

### Requirement: Native headless artifact commands remain raw inspection surfaces
`houmao-mgr agents turn stdout` and `houmao-mgr agents turn stderr` SHALL remain raw artifact inspection commands for managed headless turns.

Those commands SHALL not reinterpret raw provider artifacts as canonical semantic events or rendered human output.

#### Scenario: Native stdout inspection returns raw provider artifact text
- **WHEN** an operator runs `houmao-mgr agents turn stdout <agent-ref> <turn-id>`
- **THEN** the command returns the raw stdout artifact text for that headless turn
- **AND THEN** it does not substitute canonical semantic JSON or rendered live-pane text for that raw artifact
