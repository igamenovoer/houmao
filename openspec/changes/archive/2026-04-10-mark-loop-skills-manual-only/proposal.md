## Why

`houmao-agent-loop-pairwise` and `houmao-loop-planner` currently describe themselves as normal packaged skills that can be selected whenever a request matches their scope. That makes them too easy to auto-route into, even though both skills represent heavyweight, operator-directed loop-planning workflows that should only run when the user explicitly chooses them.

## What Changes

- Mark `houmao-agent-loop-pairwise` as manual-invocation-only and require its top-level guidance to say that agents must not auto-route generic pairwise loop-planning or run-control requests into that skill.
- Mark `houmao-loop-planner` as manual-invocation-only and require its top-level guidance to say that agents must not auto-route generic loop-bundle authoring, distribution-preparation, or handoff requests into that skill.
- Clarify the entrypoint scenarios for both skills so explicit user invocation by skill name remains supported while ordinary loop-related requests stay outside these packaged skill entrypoints by default.
- Update the packaged skill content and projection tests to assert the new manual-only guidance for both skill manifests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-skill`: require the packaged pairwise loop skill to be manual-invocation-only instead of a generic auto-routed loop entrypoint.
- `houmao-loop-planner-skill`: require the packaged loop-planner skill to be manual-invocation-only instead of a generic auto-routed planning entrypoint.

## Impact

- Affected packaged skill manifests under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise/` and `src/houmao/agents/assets/system_skills/houmao-loop-planner/`
- Affected OpenSpec capability definitions for the pairwise loop skill and the loop-planner skill
- Affected packaged system-skill content tests under `tests/unit/agents/`
- No new runtime API, storage format, or manager command surface
