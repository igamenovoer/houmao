## Why

Agents following Houmao-owned system skills can encounter both foreground and background gateway launch surfaces, but the skill guidance does not consistently state that foreground same-session tmux execution is the default path and background execution is an explicit user choice. This creates avoidable confusion during tours and multi-agent setup, especially when the desired outcome is an observable tmux session with the agent on window `0` and the gateway in a non-zero auxiliary window.

## What Changes

- Update gateway lifecycle guidance so `houmao-mgr agents gateway attach` is taught as foreground-first by default for tmux-backed sessions.
- Update launch-time gateway guidance for specialist-backed and general managed-agent launch paths so agents do not add background gateway flags unless the user explicitly asks for detached background execution.
- Update guided touring launch guidance so first-run tours prefer visible tmux foreground posture, explain non-interactive tmux handoff separately from gateway background execution, and treat background gateway launch as an explicit user intent.
- Update composition guidance that points agents at gateway attach so it delegates to the same foreground-first rule instead of leaving posture implicit.
- No breaking changes to CLI flags, command behavior, or gateway runtime contracts.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-gateway-skill`: gateway lifecycle guidance must present same-session foreground attach as the default and background attach as explicit user intent.
- `houmao-create-specialist-skill`: specialist-backed easy launch guidance must explain default foreground auto-attached gateway posture and avoid background gateway flags unless explicitly requested.
- `houmao-manage-agent-instance-skill`: managed-agent launch guidance must preserve foreground-first gateway posture across role/preset, launch-profile, and specialist-backed launch lanes.
- `houmao-touring-skill`: guided tour launch branches must advise foreground-first gateway posture for visible first-run tours and distinguish non-interactive tmux handoff from detached gateway execution.
- `houmao-adv-usage-pattern-skill`: composition pages that mention gateway attach must defer to the foreground-first gateway lifecycle rule rather than treating background attach as implicit or default.

## Impact

- Affected assets: `src/houmao/agents/assets/system_skills/houmao-agent-gateway/`, `houmao-specialist-mgr/`, `houmao-agent-instance/`, `houmao-touring/`, and relevant `houmao-adv-usage-pattern/` pattern pages.
- Affected specs: the five modified Houmao system-skill specs listed above.
- Affected tests: system-skill packaging/content tests under `tests/unit/agents/test_system_skills.py` and any targeted tests that assert installed skill text.
- No CLI behavior, public API, dependency, or data format changes are intended.
