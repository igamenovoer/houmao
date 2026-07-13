## ADDED Requirements

### Requirement: Codex GPT-5.6 reasoning ladders follow the bundled Codex model catalog
Houmao SHALL resolve Codex GPT-5.6 reasoning presets from model-specific maintained ladders rather than from the four-level legacy fallback.

The maintained ladders SHALL be:

- `gpt-5.6`, `gpt-5.6-sol`, and `gpt-5.6-terra`: `1=low`, `2=medium`, `3=high`, `4=xhigh`, `5=max`, `6=ultra`
- `gpt-5.6-luna`: `1=low`, `2=medium`, `3=high`, `4=xhigh`, `5=max`

Values above a ladder SHALL saturate to its final value. Level `0` SHALL be rejected for these ladders because the Codex CLI catalog does not advertise an off preset for them.

#### Scenario: Sol level six selects delegation-capable ultra effort
- **WHEN** a Codex launch selects `gpt-5.6-sol` with reasoning level `6`
- **THEN** Houmao projects `model_reasoning_effort = "ultra"`
- **AND THEN** the projection provenance records that level `6` did not saturate

#### Scenario: Luna saturates above max
- **WHEN** a Codex launch selects `gpt-5.6-luna` with reasoning level `9`
- **THEN** Houmao projects `model_reasoning_effort = "max"`
- **AND THEN** the projection provenance records saturation

#### Scenario: GPT-5.6 rejects off
- **WHEN** a Codex launch selects a maintained GPT-5.6 model with reasoning level `0`
- **THEN** Houmao rejects the reasoning request clearly

### Requirement: Kimi reasoning levels use selected-model effort capabilities
For a config-backed Kimi model alias, Houmao SHALL derive the positive reasoning ladder from that alias's ordered effective on-disk `support_efforts` declaration after applying Kimi model overrides. It SHALL project a selected positive effort through Kimi's native thinking configuration for both TUI and headless launches.

Houmao SHALL reject a launch-owned Kimi reasoning level when the selected alias has no trustworthy ordered effort declaration. Current Kimi env-model inputs expose no ordered effort catalog, so Houmao SHALL reject normalized reasoning requests for that lane rather than infer a ladder from `KIMI_MODEL_THINKING_EFFORT`. Native effort env configuration SHALL remain unchanged when no normalized reasoning request is supplied.

Level `0` SHALL disable thinking only when the selected Kimi model contract permits an off state. Models declared always-thinking SHALL reject level `0`.

#### Scenario: Kimi alias maps ordered efforts
- **WHEN** the selected Kimi alias declares effective efforts `low`, `high`, and `max`
- **AND WHEN** the launch-owned reasoning level is `2`
- **THEN** Houmao projects Kimi thinking enabled with effort `high`

#### Scenario: Kimi missing effort metadata is rejected
- **WHEN** a Kimi launch requests reasoning level `1`
- **AND WHEN** the selected model inputs expose no ordered effort capability
- **THEN** Houmao rejects the request with a model-specific diagnostic
- **AND THEN** it does not invent a low-to-high ladder
