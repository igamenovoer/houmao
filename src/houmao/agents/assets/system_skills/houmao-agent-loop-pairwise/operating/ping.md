# Ping A Pairwise Loop Participant

Use this page when the user wants to actively ask one selected pairwise-loop participant what is going on.

## Workflow

1. Resolve the target `run_id` and the selected agent name.
2. Keep the target narrow. `ping` is for one selected agent, not a broadcast.
3. Send one concise progress question through `houmao-agent-messaging`.
4. Include only the control context needed for that question:
   - `run_id`
   - the participant role when helpful
   - the specific posture or progress question the user wants answered
5. Present the reply as active-message output, not as though it came from read-only inspection.

## Ping Contract

- `ping <agent-name>` is active messaging.
- `ping` is distinct from `peek`.
- `ping` may help clarify stale or ambiguous posture after read-only inspection, but it is not the canonical inspection verb.

## Guardrails

- Do not use `ping` as a synonym for `peek`.
- Do not broadcast ping every participant as a substitute for `peek all`.
- Do not silently widen delegation authority or change stop posture while sending a ping.
