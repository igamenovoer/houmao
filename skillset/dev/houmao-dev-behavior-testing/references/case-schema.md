# Behavior Case Schema

## Workflow

1. **Resolve the catalog row and family defaults.** Treat the row plus its linked family page as one case definition.
2. **Validate every required field** from **Resolved Fields** before planning an attempt.
3. **Expand inherited defaults** into the frozen run manifest so execution never depends on mutable implicit values.
4. **Bind the semantic oracle and exact stimulus** by digest before provider launch.
5. **Reject unknown activation modes, verdict requirements, or effect boundaries.**

If a new case needs a field the schema cannot represent, use the native planning tool to revise this schema and catalog explicitly before executing the case; do not hide the value in evaluator prose.

## Resolved Fields

| Field | Contract |
| --- | --- |
| `case_id` | Stable uppercase family prefix and three digits, such as `ADM-003` |
| `case_revision` | Positive integer incremented when stimulus or semantic oracle changes |
| `title` | Short human-readable scenario name |
| `family` | `activation`, `admin-routing`, `managed-agent-routing`, `shared-routines`, `loops`, or `generated-prompts` |
| `providers` | Explicit subset of `claude`, `codex`, and `kimi`, or a recorded unsupported reason |
| `context_type` | One named fixture context from `fixture-contexts.md` |
| `required_pack` | `admin`, `agent`, `admin+agent`, or `none` |
| `auto_skill_posture` | `present-required`, `absent-required`, or `not-applicable` |
| `activation_mode` | `implicit`, `explicit`, `generated-prompt`, or `lifecycle` |
| `stimulus` | Exact prompt or ordered multi-turn stimulus; placeholders resolve before freeze |
| `expected_root` | Expected top-level skill, `none`, or a parameterized root matrix |
| `expected_route` | Expected sibling/child/operation path, `none`, or an explicitly unobservable route |
| `required_observables` | Concrete events, commands, gates, response meanings, or state transitions required to pass |
| `forbidden_observables` | Roots, routes, commands, actor transitions, mutations, or claims that fail the case |
| `permitted_effects` | Bounded paths and runtime resources the attempt may change |
| `evidence_requirements` | Minimum evidence kinds needed for each required verdict dimension |
| `repetitions` | Positive count; default `3` |
| `timeout_seconds` | Positive observation limit or an explicit lifecycle boundary |
| `stop_condition` | Terminal response, clarification, bounded effect, generated round completion, or lifecycle event |
| `cleanup` | Sessions, temporary homes, agents, gateways, mailboxes, and files to restore or remove |

## Inheritance

A family page may declare common providers, context, pack, auto-skill posture, repetitions, timeout, evidence requirements, permitted root, and cleanup. A case table cell may say `family default`, but the planned `run-manifest.json` must contain the expanded value. Stimulus, expected root, required behavior, and forbidden behavior are never inherited from another case.

## Revision Rules

Increment `case_revision` when the exact stimulus, expected root/route, required or forbidden behavior, permitted effects, stop condition, or evidence minimum changes. Provider additions, clarified prose, and timeout changes also increment revision when they can affect results. Catalog ordering alone does not.

## Guardrails

- DO NOT execute a case with unresolved placeholders.
- DO NOT let family defaults remain implicit in a frozen run manifest.
- DO NOT change an oracle without incrementing the case revision.
