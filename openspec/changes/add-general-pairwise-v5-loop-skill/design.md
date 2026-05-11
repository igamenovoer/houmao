## Context

Houmao currently packages a family of pairwise loop skills through v4. Those skills author and operate Markdown-centered loop plans, with v4 adding stricter document templates and source-constraint coverage. The next workflow needs a more explicit two-phase model: an editable source area where the user and agent shape loop intention, and a generated execution package that participant agents can consume through structured contracts, installable role skills, concrete agent bindings, generated docs, and a plan-local harness.

The v7 Hopper loop-plan directory is useful as a reference for the generated execution package shape, but v5 itself must be domain-neutral. CUDA optimization, Hopper constraints, ADR harvesting, and task-specific loop policy are not part of the packaged v5 skill contract.

Stakeholders are:

- operators who manually invoke v5 and choose the loop directory,
- the authoring agent that creates and refines intention material,
- execution agents that consume the generated `execplan/`,
- maintainers of Houmao packaged system skills and installation surfaces.

## Goals / Non-Goals

**Goals:**

- Add a packaged `houmao-agent-loop-pairwise-v5` system skill.
- Make v5 manual-invocation-only.
- Require implementation to invoke `$skill-creator` before creating or substantially updating v5 skill assets.
- Require the user to provide `<loop-dir>` before the skill writes files.
- Define `<loop-dir>/intention/` as a freeform editable source area with `README.md` and `loop-overview.md`.
- Define `<loop-dir>/execplan/` as a generated package shaped like the current v5 loop-plan reference: `manifest.toml`, `specs/`, `skills/`, `agents/`, `harness/`, and `docs/`.
- Split skill guidance into authoring and execution subskills so each operational mode has bounded instructions.
- Keep v5 general across domains and independent from CUDA/Hopper assumptions.

**Non-Goals:**

- Implement a CUDA-specific loop generator.
- Require or parse `adrs/` as part of the initial v5 workflow.
- Preserve compatibility with the v4 generated Markdown bundle format.
- Add a generic loop engine to Houmao core.
- Automatically invoke v5 for generic loop requests.
- Make generated `execplan/` files the user-editable source of truth.

## Decisions

### Decision: Use one required `<loop-dir>` with separate `intention/` and `execplan/` subtrees

V5 work is rooted in a user-selected `<loop-dir>`. The skill must not invent this directory or scatter v5 outputs across unrelated locations. Under that root, `intention/` is the editable source area and `execplan/` is the generated execution package.

Rationale: a single root makes a loop easy to copy, review, regenerate, and archive while keeping source and generated material visibly separated.

Alternative considered: continue the v4 pattern of a selected plan-output directory containing `plan.md` and support files. Rejected because v5 needs a durable source-to-generated boundary, not one authored Markdown bundle that doubles as execution material.

### Decision: Treat `intention/` as mostly freeform source

The authoring subskills create `intention/README.md` to explain the area and `intention/loop-overview.md` as the human entrypoint. Other Markdown files may be added by the user or agent without a strict schema. User edits are expected.

Rationale: early loop design is exploratory. A rigid source schema would fight the way operators and agents refine intent.

Alternative considered: require strict intention templates from the first v5 version. Rejected because the user explicitly wants freeform intention Markdown and later ADR support can add stronger structure if needed.

### Decision: Treat `execplan/` as generated operational material

The generated `execplan/` package uses the current v5-style loop-plan layout:

```text
execplan/
  manifest.toml
  specs/
  skills/
  agents/
  harness/
  docs/
```

`manifest.toml` is the discovery and artifact index. `specs/` contains abstract loop contracts, `skills/` contains generated event or utility skills, `agents/` binds concrete agents to abstract participants, `harness/` contains plan-local execution helpers, and `docs/` contains generated human support material.

Rationale: this keeps machine contracts, generated role behavior, concrete agent initialization, execution helpers, and explanatory docs distinct.

Alternative considered: reuse the older prototype layout with `manifest.json`, `objective/`, `topology/`, `roles/`, `policies/`, `protocols/`, `email/`, `state/`, `harness/`, `docs/`, and `views/`. Rejected because the current reference layout has already moved to the clearer `specs/`, `skills/`, `agents/`, `harness/`, and `docs/` split.

### Decision: Split the packaged skill into authoring and execution subskills

The top-level `SKILL.md` should route to subskills instead of carrying the full procedure. Initial authoring subskills should cover creating intention material, refining intention, generating an execplan, validating an execplan, and regenerating an execplan. Initial execution subskills should cover preparing agents, starting, checking status, pausing, resuming, recovering, and stopping.

Rationale: v5 is too complex for one instruction file. Subskills reduce process drift and let future changes evolve authoring and execution independently.

Alternative considered: one large top-level `SKILL.md`. Rejected because it would be hard to follow, hard to test, and likely to blur authoring with execution.

### Decision: Keep v5 manual-invocation-only

The skill activates only when the user explicitly requests `houmao-agent-loop-pairwise-v5` or the exact v5 operation. Generic loop planning must not silently route to v5.

Rationale: v5 can create directories, generate operational artifacts, and control agent loops. That is high-impact work and should require explicit operator intent.

Alternative considered: auto-route generic loop requests to the newest pairwise skill. Rejected because the existing pairwise family already treats advanced loop skills as explicit selections.

### Decision: Use `$skill-creator` when creating the packaged v5 skill

The implementation pass must invoke `$skill-creator` before creating or substantially updating the `houmao-agent-loop-pairwise-v5` skill assets. The implementer should apply the skill-creator guidance for skill anatomy, concise instructions, progressive disclosure, `agents/openai.yaml`, resource placement, and validation. If the packaged-system-skill location makes a generic initializer command unsuitable, the implementer should still follow the skill-creator workflow principles and note the reason in the implementation summary.

Rationale: v5 is itself a complex skill. Using the existing skill-creation guidance reduces drift in frontmatter, trigger descriptions, subskill organization, resource layout, and validation.

Alternative considered: author the v5 skill directly by copying v4 patterns. Rejected because v5 introduces a different source-to-generated execution model and benefits from the general skill-authoring guardrails.

### Decision: Defer ADR handling

The initial v5 skill does not require an `adrs/` directory, does not scan ADRs, and does not validate ADR coverage. ADR support can be introduced later as an authoring enhancement.

Rationale: the first version should prove the `intention/` to `execplan/` model without coupling it to a specific design-document governance workflow.

Alternative considered: require ADRs because the v7 Hopper reference uses them. Rejected because the user explicitly wants ADRs handled later.

## Risks / Trade-offs

- [Freeform intention can be ambiguous] -> Mitigate by making `loop-overview.md` the human entrypoint and requiring generation to surface unresolved assumptions instead of silently inventing them.
- [Generated execplans may be hand-edited] -> Mitigate by labeling `execplan/` generated and requiring regeneration from `intention/` as the normal update path.
- [Manual-only activation limits discoverability] -> Mitigate through catalog descriptions and optional documentation, while preserving explicit operator control.
- [General v5 requirements may under-specify domain behavior] -> Mitigate by keeping domain-specific policy inside the user-authored intention and generated per-loop specs, not in the packaged v5 skill.
- [Execution subskills can overlap existing Houmao operation skills] -> Mitigate by routing platform operations to maintained skills such as instance, messaging, mailbox, gateway, memory, and inspect skills.

## Migration Plan

1. Invoke `$skill-creator` and apply its guidance to the packaged v5 skill design.
2. Add the new packaged `houmao-agent-loop-pairwise-v5` skill assets.
3. Register v5 in the system-skill catalog and expected install sets.
4. Add tests that v5 is packaged, installable, manual-only, and organized by subskills.
5. Add tests or fixture checks for the required v5 directory vocabulary: `<loop-dir>/intention/` and `<loop-dir>/execplan/`.
6. Leave existing pairwise, v2, v3, and v4 skills unchanged.

Rollback is to remove the v5 skill assets and catalog entry. Existing loop skills and user-authored v4 bundles are unaffected.

## Open Questions

- Should the first implementation include a helper script for deterministic `execplan/` generation, or should generation be instruction-driven only?
- Should v5 be included in the default `core` and `all` install sets immediately, or only in `all` until the workflow matures?
- What minimum `execplan/harness/` surface is required for the first execution-capable version?
