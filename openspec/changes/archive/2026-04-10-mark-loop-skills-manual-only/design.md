## Context

Houmao already packages two higher-level loop workflow skills:

- `houmao-agent-loop-pairwise` for pairwise loop plan authoring and run control
- `houmao-loop-planner` for operator-owned loop bundle authoring and runtime handoff preparation

Both top-level `SKILL.md` files currently advertise broad "use this skill when..." routing language. In practice, that makes them eligible for automatic selection whenever a user asks for loop planning or loop control work, even when the user did not explicitly ask to invoke those packaged workflows.

The requested change is narrower than a runtime refactor. It changes entrypoint policy, not loop semantics. The important constraints are:

- both skills remain packaged and installable,
- their internal authoring, distribution, handoff, and operating pages remain intact,
- the change should only narrow when the skills are selected,
- `houmao-loop-planner` is still defined in the open change `add-houmao-loop-planner-skill`, so this proposal must stack cleanly on top of that not-yet-archived capability definition.

## Goals / Non-Goals

**Goals:**

- Require `houmao-agent-loop-pairwise` to state that it is manual-invocation-only.
- Require `houmao-loop-planner` to state that it is manual-invocation-only.
- Preserve explicit invocation by skill name for both skills.
- Make generic loop-related requests stay outside these packaged skill entrypoints unless the user explicitly selects them.
- Cover the new entrypoint policy with packaged skill content tests.

**Non-Goals:**

- Changing pairwise loop semantics, delegation policy, stop behavior, or reporting behavior
- Changing loop bundle structure, runtime handoff templates, or lower-level routing
- Removing either skill from the packaged catalog
- Introducing a new generic loop router or new CLI/API surface

## Decisions

### Express manual-only policy in the top-level requirement for each skill

The change should modify the primary "Houmao provides a packaged ... system skill" requirement for each skill rather than adding a disconnected follow-on requirement.

Why:

- The manual-only rule is part of the skill's identity and entrypoint contract.
- Keeping it in the top-level packaged-skill requirement makes archive output easier to read and keeps the routing policy next to the skill-description language it constrains.

Alternative considered:

- Adding a separate requirement only for invocation posture. Rejected because it would split one skill-entrypoint contract across multiple requirement blocks and make future edits easier to miss.

### Treat manual invocation as explicit user selection by skill name

For both skills, "manual invocation only" should mean the user explicitly asks for the named skill rather than merely describing a loop-related goal in generic terms.

Why:

- The user's request is about stopping automatic routing into these heavyweight skills.
- Exact skill-name invocation is the clearest boundary and matches the style already used by other manual-only Houmao skills.

Alternative considered:

- Allowing broad intent matches such as any pairwise-loop request or any loop-planner-like request to count as manual enough. Rejected because that would preserve the ambiguity the user wants removed.

### Add an explicit non-auto-routing scenario for each skill

Each modified capability spec should include a scenario showing that ordinary loop-related requests do not auto-route to the skill when the user did not explicitly invoke it.

Why:

- The change is mainly about what must not happen.
- A negative routing scenario is straightforward to test against the packaged skill text and documents the intended boundary clearly for future maintainers.

Alternative considered:

- Relying only on positive explicit-invocation scenarios. Rejected because that would leave the new constraint implicit.

### Stack the loop-planner delta on the current open capability definition

The loop-planner side of this change should target the existing `houmao-loop-planner-skill` capability definition that currently lives under the open change `add-houmao-loop-planner-skill`.

Why:

- The repo already contains the proposed loop-planner capability definition even though it is not archived into `openspec/specs/` yet.
- Capturing the manual-only delta now keeps the pairwise and planner entrypoint policy aligned.

Alternative considered:

- Deferring the loop-planner part until after `add-houmao-loop-planner-skill` is archived. Rejected because it would leave the two loop skills inconsistent and force a follow-up change for the same policy.

## Risks / Trade-offs

- [The loop-planner capability is still defined in an open change rather than `openspec/specs/`] -> Mitigation: record the stacked dependency explicitly in the design and keep the delta limited to the top-level packaged-skill requirement so it is easy to merge or replay.
- [Some future maintainer may interpret "manual invocation" more loosely than exact skill-name selection] -> Mitigation: state the policy in normative language and include a non-auto-routing scenario for generic requests.
- [Tests may only assert packaging presence and miss the new routing boundary] -> Mitigation: add content assertions for the manual-only wording in both `SKILL.md` files.

## Migration Plan

1. Update the pairwise skill capability spec to require manual invocation by explicit skill-name request and to forbid auto-routing from generic pairwise loop requests.
2. Update the loop-planner capability spec with the same manual-only entrypoint policy, stacking the delta on the existing open capability definition.
3. Revise both packaged `SKILL.md` files so their top-level guidance states the manual-only rule clearly.
4. Update packaged skill content tests to assert the new wording for both skills.
5. During implementation or archive, ensure the loop-planner delta is merged with the still-open `add-houmao-loop-planner-skill` capability before final archival into `openspec/specs/`.

Rollback is low risk: revert the spec deltas, restore the previous `SKILL.md` wording, and remove the new content assertions.

## Open Questions

- None. The change narrows skill entrypoint policy without altering loop behavior or runtime ownership.
