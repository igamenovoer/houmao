## Why

`houmao-agent-loop-pairwise` currently has broad lanes like authoring, prestart, and operating, but it does not define one canonical lifecycle vocabulary for operator actions and observed run states. That makes commands like `peek`, `ping`, `pause`, `resume`, and `stop` easy to interpret differently across docs, prompts, and future implementations.

## What Changes

- Define one canonical operator action vocabulary for pairwise loop control:
  - `plan`
  - `initialize`
  - `start`
  - `peek master`
  - `peek all`
  - `peek <agent-name>`
  - `ping <agent-name>`
  - `pause`
  - `resume`
  - `stop`
  - optional `broadcast-stop` as a distinct advisory action, not a synonym for `stop`
- Define one canonical observed loop-state vocabulary that stays separate from operator actions:
  - `authoring`
  - `initializing`
  - `awaiting_ack`
  - `ready`
  - `running`
  - `paused`
  - `stopping`
  - `stopped`
  - `dead`
- Clarify the semantic boundary between read-only inspection and active messaging:
  - `peek` is read-only inspection
  - `ping` is an active message to a selected agent
- Clarify `pause` and `resume` semantics so they describe actual loop wakeup control rather than only mail-notifier toggling.
- Clarify that `stop` remains the master-directed termination action for the pairwise run, while any participant-wide advisory email remains a separate optional action.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-skill`: define canonical lifecycle action names, canonical observed loop states, and precise semantics for `peek`, `ping`, `pause`, `resume`, and `stop`

## Impact

- Affected specs: `openspec/specs/houmao-agent-loop-pairwise-skill/spec.md`
- Affected docs/assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise/**`
- Likely follow-on updates: system-skill overview docs, pairwise tests, and any prompt or template text that currently uses broader or ambiguous lifecycle wording
