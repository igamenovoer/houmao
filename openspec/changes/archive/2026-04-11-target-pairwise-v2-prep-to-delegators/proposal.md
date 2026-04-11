## Why

`houmao-agent-loop-pairwise-v2` currently describes `initialize` as a preparation wave that sends standalone preparation mail to every participant before the master trigger. That is too noisy for leaf participants, because leaf agents receive actionable context through the actual downstream delegation message and do not need a prestart mail by default.

## What Changes

- Change the v2 pairwise `initialize` default so preparation mail is sent only to participants that have descendants, meaning participants expected to delegate jobs to other agents.
- Keep leaf participants out of the default preparation-mail target set unless the user explicitly asks to include leaf agents.
- Keep authored participant preparation material available for all participants so plans remain explicit, but distinguish preparation material from the default mail delivery target set.
- Define acknowledgement handling against the actual preparation recipients: `require_ack` waits only for targeted preparation recipients unless the user explicitly includes leaf agents.
- Update v2 prestart, start, plan-structure, template, and test expectations so the targeted preparation behavior is visible and verifiable.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v2-skill`: change the v2 prestart preparation requirement so `initialize` targets delegating/non-leaf participants by default and includes leaf participants only on explicit user request.

## Impact

- Affected assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/` guidance and templates.
- Affected tests: packaged system-skill content assertions for the v2 pairwise prestart, start, and template surfaces.
- Affected behavior: user-controlled v2 pairwise initialization becomes less noisy for leaf agents while preserving an explicit override for all-participant preparation.
