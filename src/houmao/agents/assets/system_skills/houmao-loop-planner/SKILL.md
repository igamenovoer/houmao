---
name: houmao-loop-planner
description: Use Houmao's loop-planning skill when a user-controlled agent needs to author one operator-owned loop bundle in a user-designated directory, prepare participant and distribution guidance, or prepare runtime handoff for pairwise or relay loops.
license: MIT
---

# Houmao Loop Planner

Use this Houmao skill when a user-controlled agent needs to author or revise one operator-owned loop bundle in a user-designated directory before any live run starts.

`houmao-loop-planner` is intentionally above `houmao-agent-loop-pairwise` and `houmao-agent-loop-relay`. This skill does not invent a new runtime loop engine. It turns user intent into one static bundle that is easy for humans to read, revise, and distribute, with Markdown-first documents for meaning and small TOML files only where machine-shaped metadata is actually helpful.

The trigger word `houmao` is intentional. Use the `houmao-loop-planner` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers three lanes:

- authoring or revising one loop bundle
- preparing participant and distribution guidance
- preparing runtime handoff templates

This packaged skill does not cover:

- writing the authored bundle under `HOUMAO_JOB_DIR` or `HOUMAO_MEMORY_DIR`
- sending bundle artifacts to participants automatically
- starting, monitoring, or stopping live runs itself
- replacing `houmao-agent-loop-pairwise`, `houmao-agent-loop-relay`, or `houmao-adv-usage-pattern`

## Workflow

1. Confirm that the user wants one operator-owned loop bundle rather than an immediate live run-control action.
2. Keep two stages separate from the start:
   - planning stage: author the bundle in a user-designated directory
   - runtime stage: later route live execution to the existing pairwise or relay runtime skill
3. Keep the bundle Markdown-first:
   - `plan.md`
   - `participants.md`
   - `execution.md`
   - `distribution.md`
4. Keep TOML minimal:
   - `profile.toml`
   - `runs/charter.template.toml`
5. If the user needs a new bundle or a revised bundle, load exactly one authoring page:
   - `authoring/formulate-loop-bundle.md`
   - `authoring/revise-loop-bundle.md`
   - `authoring/render-loop-graph.md`
6. If the user needs participant, execution, or distribution material prepared, load exactly one distribution page:
   - `distribution/prepare-participants.md`
   - `distribution/prepare-execution.md`
   - `distribution/prepare-distribution.md`
7. If the user needs runtime handoff prepared, load exactly one handoff page:
   - `handoff/prepare-run-charter.md`
   - `handoff/route-to-runtime-skill.md`
8. Use the local references and templates only when they help keep the bundle simple, structured, and operator-owned.

## Authoring Pages

- Read [authoring/formulate-loop-bundle.md](authoring/formulate-loop-bundle.md) when the user has a goal but not yet one valid loop bundle.
- Read [authoring/revise-loop-bundle.md](authoring/revise-loop-bundle.md) when an existing bundle needs to be tightened, simplified, or updated without changing the high-level objective.
- Read [authoring/render-loop-graph.md](authoring/render-loop-graph.md) when `plan.md` needs the final Mermaid graph that shows the operator outside the execution loop, the master role, the topology, and the supervision, completion, and stop checkpoints.

## Distribution Pages

- Read [distribution/prepare-participants.md](distribution/prepare-participants.md) when the bundle needs `participants.md`.
- Read [distribution/prepare-execution.md](distribution/prepare-execution.md) when the bundle needs `execution.md`.
- Read [distribution/prepare-distribution.md](distribution/prepare-distribution.md) when the bundle needs `distribution.md`.

## Handoff Pages

- Read [handoff/prepare-run-charter.md](handoff/prepare-run-charter.md) when the bundle needs `runs/charter.template.toml`.
- Read [handoff/route-to-runtime-skill.md](handoff/route-to-runtime-skill.md) when the user is ready to route later live activation to `houmao-agent-loop-pairwise` or `houmao-agent-loop-relay`.

## References

- Read [references/dir-structure.md](references/dir-structure.md) for the canonical bundle directory structure.
- Read [references/section-conventions.md](references/section-conventions.md) for the required section shapes in `participants.md`, `execution.md`, and `distribution.md`.
- Read [references/profile-schema.md](references/profile-schema.md) for the minimal `profile.toml` fields.
- Read [references/charter-template-schema.md](references/charter-template-schema.md) for the minimal `runs/charter.template.toml` fields.
- Read [references/storage-rules.md](references/storage-rules.md) for the operator-owned storage boundaries and the prohibition on agent-local runtime directories.

## Templates

- Read [templates/plan.md](templates/plan.md) for the canonical `plan.md` entrypoint.
- Read [templates/participants.md](templates/participants.md) for the participant-section format.
- Read [templates/execution.md](templates/execution.md) for the shared execution guidance format.
- Read [templates/distribution.md](templates/distribution.md) for the operator distribution playbook format.
- Read [templates/profile.toml](templates/profile.toml) for the minimal profile metadata file.
- Read [templates/charter.template.toml](templates/charter.template.toml) for the run handoff template.

## Routing Guidance

- Route later live pairwise run control to `houmao-agent-loop-pairwise`.
- Route later live relay run control to `houmao-agent-loop-relay`.
- Route downstream execution semantics to `houmao-adv-usage-pattern`.
- Treat artifact delivery as the operator's responsibility unless the user later asks for a separate messaging workflow.

## Guardrails

- Do not write the authored bundle into `HOUMAO_JOB_DIR` or `HOUMAO_MEMORY_DIR`.
- Do not replace human-readable Markdown with many small TOML policy files by default.
- Do not claim that distribution happens automatically.
- Do not present `runs/charter.template.toml` as a live start request.
- Do not present `houmao-loop-planner` as the owner of live `start`, `status`, or `stop` operations.
