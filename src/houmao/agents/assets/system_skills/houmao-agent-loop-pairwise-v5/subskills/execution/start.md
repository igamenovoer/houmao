# Start

Use this page when prepared agents and a validated execplan are ready to begin one v5 loop run.

## Inputs

Require:
- `<loop-dir>`
- generated execplan validation pass
- target run identity when the execplan or operator requires one

## Procedure

1. Validate `execplan/`.
2. Confirm required agents are live or intentionally launchable.
3. Initialize plan-local runtime state through `execplan/harness/` when the generated harness defines an initialization command.
4. Deliver the start trigger through the generated operator or lead-facing contract.
5. Use maintained Houmao messaging or mailbox skills for prompt or mail delivery.
6. Record or report the run id, addressed agents, and first expected status surface.

## Boundaries

- Do not start if `<loop-dir>` or `execplan/` is missing.
- Do not bypass generated harness initialization when the execplan defines one.
- Do not send participant work that contradicts generated role skills or generated agent bindings.
- Do not treat intention Markdown as the direct runtime contract.
