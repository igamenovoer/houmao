# Route To The Runtime Skill

Use this page when the bundle is authored and distributed and the operator needs to know which existing runtime skill owns live activation next.

## Routing

- `pairwise` -> `houmao-agent-loop-pairwise`
- `relay` -> `houmao-agent-loop-relay`

## Workflow

1. Read `profile.toml` and confirm `loop_kind`.
2. Read `distribution.md` and confirm the operator's pre-start checklist is satisfied.
3. Use `runs/charter.template.toml` as the basis for the later runtime handoff.
4. Route the live activation request to the runtime skill for the chosen loop kind.

## Guardrails

- Do not present `houmao-loop-planner` as the owner of live `start`, `status`, or `stop`.
- Do not route to a runtime skill before the bundle and operator distribution guidance are ready.
- Do not hide the `pairwise` versus `relay` choice.
