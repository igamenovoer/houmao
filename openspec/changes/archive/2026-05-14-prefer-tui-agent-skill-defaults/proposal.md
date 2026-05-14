## Why

Houmao's CLI already defaults profile-backed and specialist-backed launch paths to local interactive/TUI when headless is not explicitly requested, but the packaged system skills do not state that preference clearly. Agents following the skills can therefore overuse `--headless` or store headless posture on profiles when the user did not ask for it.

## What Changes

- Revise agent launch and profile-authoring skill guidance so omitted launch posture means "prefer TUI/local interactive when the selected tool supports it."
- Clarify that agents must only add `--headless` or store profile `--headless` when the user explicitly requests headless or when the selected tool/lane requires headless, such as Gemini.
- Keep unattended/as-is prompt mode guidance separate from TUI/headless launch posture so agents do not conflate unattended prompt mode with headless execution.
- Update fast-forward profile preparation guidance to report the intended default posture and print a launch command that does not include headless flags unless required or requested.

## Capabilities

### New Capabilities

### Modified Capabilities

- `houmao-manage-agent-definition-skill`: profile creation, raw-profile authoring, and create-agent-fast-forward guidance must prefer TUI-supported launch posture when headless is unspecified.
- `houmao-manage-agent-instance-skill`: launch guidance must prefer TUI-supported launches when headless is unspecified and avoid adding headless flags silently.
- `houmao-agent-ready-profile-workflow`: fast-forward profile preparation must distinguish prompt mode defaults from TUI/headless launch posture and default to TUI when supported.

## Impact

- Affects packaged system skill Markdown under `src/houmao/agents/assets/system_skills/houmao-agent-definition/` and `src/houmao/agents/assets/system_skills/houmao-agent-instance/`.
- No CLI behavior, database schema, runtime API, or dependency changes are expected.
- Verification should focus on skill text consistency and targeted tests or checks that packaged skill assets contain the clarified defaulting guidance.
