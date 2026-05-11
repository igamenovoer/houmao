# Extension Guide

This guide is for developers revising `houmao-agent-loop-pairwise-v5`. It is not part of the skill execution path.

## Preserve The Split

Keep these responsibilities separate:

- `SKILL.md`: activation, routing, global boundaries, and the required root vocabulary.
- `subskills/authoring/`: source creation, source refinement, execplan generation, validation, and regeneration.
- `subskills/execution/`: operating a validated execplan through generated contracts and maintained Houmao surfaces.
- `dev/design/`: rationale for maintainers only.

Do not put long design rationale into execution-facing pages. Those pages should stay concise and actionable for the active agent.

## Adding Source Inputs

The first workflow intentionally uses `intention/README.md` and `intention/loop-overview.md` as the minimum source set. If a later change adds ADRs, templates, imported source directories, or reference-plan harvesting, keep that as an explicit authoring capability and preserve the rule that `intention/` remains the normal regeneration authority.

If importing from an existing source-design directory, define a clear adapter step instead of silently treating arbitrary Markdown as a valid root.

## Tightening Generation

When tightening execplan generation, update the contract in small layers:

1. add the generated artifact requirement to the authoring subskill;
2. add matching validation checks;
3. update execution subskills only when the new artifact affects runtime behavior;
4. update these design notes with the rationale.

Prefer explicit unresolved entries over inferred behavior. A generated execplan that says what it cannot decide is easier to repair than one that hides assumptions.

## Execution Boundaries

Execution should compose existing Houmao operation surfaces. Keep managed-agent launch, mailbox, gateway, memory, lifecycle, inspection, and platform setup routed to their owning skills or supported `houmao-mgr` surfaces.

Loop-local behavior belongs in generated material:

- role instructions and event handlers under `execplan/skills/`;
- participant and concrete-agent mapping under `execplan/agents/`;
- deterministic loop state helpers under `execplan/harness/`;
- machine contracts under `execplan/specs/`.

Do not duplicate maintained Houmao platform contracts inside generated loop skills unless a later change explicitly moves ownership.

## Domain Neutrality

The packaged skill must remain domain-neutral. Domain-specific material may appear in examples, fixtures, or generated artifacts for a specific loop, but never as required global behavior.

When a domain-specific reference reveals a general need, promote the general contract rather than the domain fact. For example, promote "evidence gates belong in `specs/` and participant skills must consult them" instead of promoting one loop's exact gate values.
