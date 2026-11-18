# agent-model-selection Specification

## ADDED Requirements

### Requirement: DSH reasoning levels derive from native thinking-level escalation and preserve wire mappings

A DSH reasoning declaration SHALL be `false` or a map with at least one positive slot. For a reasoning-capable model, level `0` requires a declared `off` slot. Its positive levels SHALL select declared slots in canonical order (`minimal`, `low`, `medium`, `high`, `xhigh`, `max`) and saturate at the highest slot. Native projection SHALL preserve supported wire values for launches and request-scoped overrides.

#### Scenario: Level zero maps to declared off slot with custom wire string
- **WHEN** the selected DSH `pi-ai` model declares `reasoning_efforts` containing `off: "none"` and `high: "high"`
- **AND WHEN** the resolved launch-owned or request-scoped reasoning level is `0`
- **THEN** Houmao selects native DSH thinking slot `"off"` and projects `"reasoningEfforts": {"off": "none", "high": "high"}` into the generated model configuration

#### Scenario: Level zero maps to declared off slot with omitted wire field
- **WHEN** the selected DSH `pi-ai` model declares `reasoning_efforts` containing `'off': null` and `medium: "medium"`
- **AND WHEN** the resolved reasoning level is `0`
- **THEN** Houmao selects native DSH thinking slot `"off"` and preserves `"off": null` in the generated model configuration rather than emitting `"off": "off"`

#### Scenario: Level zero is rejected when model omits off slot
- **WHEN** the selected DSH model declares positive `reasoning_efforts` (`low`, `high`) without an `off` entry
- **AND WHEN** a launch or headless prompt requests reasoning level `0`
- **THEN** Houmao rejects the reasoning request clearly instead of promoting `0` to `low` or synthesizing `"off"`

#### Scenario: Positive levels follow canonical thinking-level order and saturate
- **WHEN** the selected DSH `pi-ai` model declares `reasoning_efforts` with keys `max: "ultra"`, `low: "low"`, and `high: "high"`
- **THEN** Houmao resolves reasoning level `1` to slot `"low"`, level `2` to slot `"high"`, level `3` to slot `"max"`, and level `8` to slot `"max"` with saturation recorded in provenance
- **AND THEN** the generated model configuration preserves `"max": "ultra"` on the wire

#### Scenario: Reasoning-disabled DSH model accepts level zero and rejects positive levels
- **WHEN** the selected DSH model declares `reasoning_efforts: false`
- **THEN** reasoning level `0` or omission selects the adapter's non-reasoning posture
- **AND THEN** `pi-ai` emits `reasoningEfforts: false` on the model, omits the provider `reasoning` default, and skips ACP effort selection
- **AND THEN** DeepSeek Messages emits `thinking: disabled`
- **AND THEN** any positive reasoning level (`>= 1`) is rejected clearly before provider execution

#### Scenario: Effective reasoning map requires a positive slot
- **WHEN** a selected model's merged `reasoning_efforts` map contains only the quoted YAML key `'off'` or is empty
- **THEN** effective validation fails before provider startup and directs the author to declare a positive slot or use `reasoning_efforts: false`

#### Scenario: DeepSeek Messages can select a positive effort after an off default
- **WHEN** a reasoning-capable DeepSeek Messages model is launched at level `0` and a later ACP prompt requests a positive level
- **THEN** the launch keeps `thinking: enabled` with `reasoningEffort: off` as its default and the prompt selects the requested positive slot for that turn
- **AND THEN** an ordinary subsequent prompt can still use the materialized `off` default
