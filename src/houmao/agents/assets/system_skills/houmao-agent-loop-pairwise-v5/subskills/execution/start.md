# Start

## Preconditions

- Agents are prepared.
- Execplan is validated.
- One loop run is ready to begin.

## Inputs

Require:
- `<loop-dir>`
- generated execplan validation pass
- target run identity when the execplan or operator requires one

## Actions

1. Validate `execplan/`.
2. Confirm required agents are live or intentionally launchable.
3. Confirm generated event and tick skills are installed into the intended agents and can locate any shared harness-usage skill or harness command surface they depend on.
4. Initialize plan-local runtime state through `execplan/harness/` when the generated harness defines an initialization or bootstrap command.
5. Query or render generated objective, constraints, effective policy, participant, and state posture through `execplan/harness/` when those surfaces exist; do not ask agents to infer dynamic values from intention Markdown.
6. Deliver the start trigger through the generated operator, lead-facing, or first-participant start contract.
7. Use maintained Houmao messaging or mailbox skills for prompt or mail delivery.
8. When the start path creates structured mail or records, follow the generated TOML payload, schema validation, renderer, and controlled-apply contracts.
9. Record or report the run id, addressed agents, first expected event or tick skill, and first expected status or query surface.

## Constraints

- Do not start if `<loop-dir>` or `execplan/` is missing.
- Do not bypass generated harness initialization when the execplan defines one.
- Do not send participant work that contradicts generated role skills or generated agent bindings.
- Do not treat intention Markdown as the direct runtime contract.
- Do not bake dynamic objective, constraint, policy, ownership, or completion values into start prompts when the execplan exposes harness lookup for them.
