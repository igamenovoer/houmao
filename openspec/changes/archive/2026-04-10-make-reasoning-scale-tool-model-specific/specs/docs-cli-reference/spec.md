## MODIFIED Requirements

### Requirement: CLI reference documents headless execution overrides on all supported prompt surfaces

`docs/reference/cli/houmao-mgr.md` (and its child reference pages for `agents turn` and `agents gateway`) SHALL document the request-scoped headless execution overrides on every supported prompt submission CLI surface.

At minimum the coverage SHALL include:

- `houmao-mgr agents prompt`
- `houmao-mgr agents turn submit`
- `houmao-mgr agents gateway prompt`

For each of those three surfaces the reference SHALL document:

- `--model TEXT` as a request-scoped headless execution model override,
- `--reasoning-level INTEGER` as a tool/model-specific reasoning preset index rather than as a normalized portable `1..10` knob,
- that the interpretation of `--reasoning-level` depends on the resolved tool/model ladder and that positive overflow saturates to the highest maintained Houmao preset for that ladder,
- that the overrides apply to exactly the submitted prompt, turn, or gateway request and do not mutate launch profiles, recipes, specialists, manifests, stored easy profiles, or any other live session defaults,
- that the overrides are rejected clearly when the resolved target is a TUI-backed prompt route rather than silently dropped,
- that partial overrides (for example supplying `--reasoning-level` without `--model`) merge with launch-resolved model defaults through the shared headless resolution helper rather than resetting fields that were not explicitly overridden,
- that Gemini reasoning levels are Houmao-documented presets which may map to multiple native Gemini settings together,
- that operators who need finer native control should omit Houmao `--reasoning-level` and manage native tool config or env directly.

#### Scenario: Reader finds headless overrides on agents prompt
- **WHEN** a reader opens the `agents prompt` coverage inside `docs/reference/cli/houmao-mgr.md`
- **THEN** the page documents `--model` and `--reasoning-level` as supported options
- **AND THEN** the page states that those overrides apply to exactly the submitted prompt and never rewrite persistent launch-resolved state

#### Scenario: Reader finds headless overrides on agents turn submit
- **WHEN** a reader opens the `agents turn submit` coverage
- **THEN** the page documents `--model` and `--reasoning-level` as request-scoped overrides
- **AND THEN** the page explains that those overrides apply only to the submitted turn

#### Scenario: Reader finds headless overrides on agents gateway prompt
- **WHEN** a reader opens the `agents gateway prompt` coverage
- **THEN** the page documents `--model` and `--reasoning-level` as request-scoped overrides
- **AND THEN** the page explains that the overrides apply to exactly the addressed gateway prompt submission, including when that submission is queued through `submit_prompt`

#### Scenario: Reader understands TUI-target rejection
- **WHEN** a reader looks up any of the three supported prompt surfaces
- **THEN** the reference states that supplying `--model` or `--reasoning-level` for a TUI-backed target results in a clear failure rather than a silent drop
- **AND THEN** the reference does not suggest that TUI-backed sessions can be retargeted to a different model through these flags

#### Scenario: Reader finds Gemini preset guidance and native-control escape hatch
- **WHEN** a reader looks up reasoning-level documentation for Gemini-backed launch or prompt submission
- **THEN** the reference explains that Gemini reasoning levels are Houmao-maintained presets that may map to multiple native Gemini settings together
- **AND THEN** the reference explains that operators needing finer Gemini-native control should omit Houmao reasoning-level and manage native config or env directly
