## Why

Gemini headless unattended launches currently start as plain non-interactive `gemini -p` sessions without an explicit approval posture. Upstream Gemini CLI treats that default headless posture as read-only, which removes shell and write tools from the active tool registry and breaks managed prompt execution, gateway wake-up handling, and the maintained Gemini headless demo lane.

## What Changes

- Revise the maintained Gemini unattended launch strategy so runtime-owned `gemini_headless` starts with full tool access and no interactive approval prompts.
- Make Gemini unattended startup own the effective approval and sandbox posture even when copied setup baselines or caller-supplied low-level launch inputs request weaker or conflicting values.
- Add Gemini-specific launch-policy coverage that proves shell and file tools remain available on initial and resumed headless turns.
- Update the launch-policy reference documentation to describe the maintained Gemini unattended posture and its owned startup surfaces.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `brain-launch-runtime`: Gemini unattended headless launch policy will change from read-only-compatible startup to a full-permission no-ask posture that preserves all built-in tools across runtime-owned launches and resumed turns.
- `docs-launch-policy-reference`: The launch-policy reference will document Gemini unattended launch ownership, including approval-mode and sandbox behavior for maintained headless startup.

## Impact

- Affected runtime launch-policy assets and provider hook logic for Gemini under `src/houmao/agents/launch_policy/` and `src/houmao/project/assets/starter_agents/tools/gemini/`.
- Affected headless Gemini launch command construction under `src/houmao/agents/realm_controller/backends/` and related runtime launch tests.
- Affected launch-policy documentation in `docs/reference/build-phase/launch-policy.md`.
- Verification should include managed direct prompting and gateway-driven notifier wake-up against Gemini headless with the maintained OAuth fixture.
