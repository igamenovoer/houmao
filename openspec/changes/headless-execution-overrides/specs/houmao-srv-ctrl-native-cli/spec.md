## ADDED Requirements

### Requirement: `houmao-mgr` headless prompt commands expose request-scoped execution override flags
The native `houmao-mgr` prompt submission surfaces for headless work SHALL expose request-scoped execution override flags.

At minimum, this SHALL apply to:

- `houmao-mgr agents turn submit`
- `houmao-mgr agents gateway prompt`
- `houmao-mgr agents prompt`

Those commands SHALL accept:

- `--model <name>`
- `--reasoning-level <1..10>`

When either flag is supplied, the CLI SHALL construct request-scoped `execution.model` payload with the supplied subfields and omit unsupplied subfields so the server or gateway can inherit the remaining values from launch-resolved defaults.

`houmao-mgr agents turn submit` SHALL send that payload through the managed headless turn route.

`houmao-mgr agents gateway prompt` SHALL send that payload through the managed gateway direct prompt-control path.

`houmao-mgr agents prompt` SHALL send that payload through the transport-neutral managed-agent prompt path.

Before dispatch, `houmao-mgr agents gateway prompt` and `houmao-mgr agents prompt` SHALL resolve the addressed managed agent and reject these execution flags clearly when the resolved target is TUI-backed rather than silently dropping them.

#### Scenario: Managed headless turn submit accepts both execution flags
- **WHEN** an operator runs `houmao-mgr agents turn submit --agent-id abc123 --prompt "review this" --model gpt-5.4-mini --reasoning-level 4`
- **THEN** `houmao-mgr` submits the managed headless turn successfully
- **AND THEN** the request includes `execution.model.name = "gpt-5.4-mini"` and `execution.model.reasoning.level = 4`

#### Scenario: Transport-neutral prompt forwards partial execution override for a headless target
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id abc123 --prompt "review this" --reasoning-level 2`
- **AND WHEN** the resolved managed agent is headless
- **THEN** `houmao-mgr` submits that prompt through the supported transport-neutral managed-agent path
- **AND THEN** the request includes only the partial execution override for reasoning level `2`

#### Scenario: Gateway prompt rejects execution override for a TUI target
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "review this" --model gpt-5.4-mini`
- **AND WHEN** the resolved managed agent is TUI-backed
- **THEN** `houmao-mgr` fails that command clearly
- **AND THEN** it does not silently send a TUI gateway prompt while dropping the requested model override

#### Scenario: Invalid reasoning-level flag is rejected clearly
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id abc123 --prompt "review this" --reasoning-level 0`
- **THEN** `houmao-mgr` rejects that input clearly
- **AND THEN** the CLI does not construct or send an invalid request payload
