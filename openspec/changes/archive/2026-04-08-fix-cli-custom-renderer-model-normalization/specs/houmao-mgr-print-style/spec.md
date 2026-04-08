## MODIFIED Requirements

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
