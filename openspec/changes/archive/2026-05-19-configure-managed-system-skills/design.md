## Context

Houmao-owned system skills are packaged in `src/houmao/agents/assets/system_skills/` and selected through the packaged catalog. Today explicit `houmao-mgr system-skills install` can choose named sets or individual skills, but managed brain construction always installs the catalog's `managed_launch_sets` selection through `install_system_skills_for_home(..., auto_install_kind="managed_launch")`.

Project-local user skills are separate. Specialists and recipes already select registered project skills through the recipe `skills` list, and launch profiles can add registered or private project skills at birth time. These project skills share the same visible tool skill root as system skills, but they have different ownership, validation, and lifecycle rules.

The new design needs to let users persistently choose the system-skill surface for selected managed agents while preserving the existing safe default: omit all new fields and managed launches still install `core`.

## Goals / Non-Goals

**Goals:**

- Provide a durable system-skill selection option on easy specialists and shared launch profiles.
- Keep the existing `core` managed-launch default when no explicit policy is stored.
- Let profiles inherit, extend, replace, or disable the source specialist/recipe policy.
- Validate system-skill set and skill names against the packaged system-skill catalog.
- Make reuse-home behavior truthful by removing stale Houmao-owned current system skills that are no longer selected.
- Preserve secret-free provenance for requested and resolved system-skill policy in build/runtime metadata.

**Non-Goals:**

- Do not change `agents join` default behavior or its `--no-install-houmao-skills` escape hatch.
- Do not add a one-shot direct `agents launch` flag for ad hoc system-skill overrides in this change.
- Do not add dynamic catalog expressions, conditional catalog rules, nested sets, or aliases beyond current `core` and `all`.
- Do not merge project skills and system skills into one conceptual selection surface.

## Decisions

### Decision: Add a reusable `SystemSkillSelectionPolicy` model

Use one normalized policy shape:

```yaml
system_skills:
  mode: default | inherit | extend | replace | none
  sets:
    - core
  skills:
    - houmao-utils-llm-wiki
```

Source recipes and specialist-generated recipes allow `default`, `extend`, `replace`, and `none`; omission means `default`. Launch profiles allow `inherit`, `extend`, `replace`, and `none`; omission means `inherit`.

Alternatives considered:

- Reuse project-skill `--skill`: rejected because project skills are catalog/project-owned content while system skills are packaged Houmao-owned content.
- Store only a boolean `include_all_system_skills`: rejected because operators also need exact and additive selection, especially for a single utility skill such as `houmao-utils-llm-wiki`.
- Change the global `managed_launch_sets` default: rejected because the need is per-agent, not global.

### Decision: Store specialist policy in recipe launch payload

Specialists already compile to a generated compatibility recipe, and that recipe owns launch defaults such as `prompt_mode`, model selection, and env records. Store the specialist's system-skill policy under `launch.system_skills` in the generated preset YAML and parse the same field from manually authored recipes.

This gives explicit recipe-backed launch profiles a source policy to inherit when users manually author or patch recipes outside the easy specialist lane.

Alternative considered:

- Store policy only in specialist catalog rows: rejected because the managed build path consumes parsed recipe launch state and would leave low-level recipes without the same capability.

### Decision: Store launch-profile policy as profile-owned birth-time config

Add launch-profile storage for `system_skills_payload` and project it under `defaults.system_skills` in `.houmao/agents/launch-profiles/<name>.yaml`. Easy profiles and explicit launch profiles share this storage and mutation behavior.

Patch semantics preserve the stored policy when no system-skill option is supplied. Replacement semantics clear it unless the replacement request supplies a new policy, matching other optional launch-profile defaults.

Alternative considered:

- Put profile system-skill policy inside the existing `defaults.skills` object: rejected because `defaults.skills` currently means project registered/private skill overlays, not packaged Houmao system skills.

### Decision: Resolve policy before build and sync installed system skills

Launch resolution should pass the source recipe policy and optional launch-profile policy into `BuildRequest`. `BrainBuilder` resolves the effective selection:

```text
source omitted/default -> catalog.auto_install.managed_launch_sets
source extend          -> managed_launch_sets + requested sets/skills
source replace         -> requested sets/skills only
source none            -> empty selection

profile inherit        -> source effective selection
profile extend         -> source effective selection + requested sets/skills
profile replace        -> requested sets/skills only
profile none           -> empty selection
```

For fresh homes this is straightforward. For reused homes, a replace or none policy must also remove current Houmao-owned system-skill paths that are no longer selected; otherwise a previously installed utility skill can linger. Implement this as a managed-home sync helper that removes exact catalog-known current/retired Houmao-owned paths and then projects the resolved current selection. It must preserve unknown user skill paths.

Alternative considered:

- Keep using `install_system_skills_for_home` unchanged: rejected because it does not remove unselected current skills from reused homes.

### Decision: Reject project/private skill name collisions with current system skills

Because project skills and system skills project into the same visible tool skill root, a project or private skill named like a current Houmao system skill is ambiguous and can be removed by system-skill synchronization. Managed builds should reject selected registered/private project skill names that match any current packaged system-skill name.

Alternative considered:

- Allow project/private skills to shadow system skills: rejected because it makes provenance and reuse-home cleanup hard to reason about.

### Decision: Keep CLI defaults concise

CLI options use explicit `system-skill` wording:

```text
--system-skill-set <set>
--system-skill <skill>
--system-skills-mode default|inherit|extend|replace|none
--clear-system-skills
--no-system-skills
```

When selectors are provided without a mode, source commands infer `extend`, and profile commands infer `extend`. `--no-system-skills` is shorthand for `mode=none`. `--clear-system-skills` clears stored source/profile policy so source falls back to `default` and profile falls back to `inherit`.

## Risks / Trade-offs

- Reused homes can contain stale skill paths -> The managed sync helper removes exact catalog-known current and retired Houmao-owned paths before projecting the resolved selection.
- Existing project skills that use a Houmao system-skill name may start failing managed builds -> This is preferable to silent shadowing; error messages should explain the naming collision and ask operators to rename the project/private skill.
- Catalog migration touches central project state -> Bump the catalog schema, add a default empty JSON payload, and treat missing payload as omitted policy.
- Older Houmao versions may reject generated recipes containing `launch.system_skills` -> This repository allows breaking changes during active development; rollback guidance is to clear the stored policy or regenerate recipes without the field before downgrading.
- Too many modes can confuse users -> CLI help and docs should emphasize the two common cases: omit for `core`, or pass `--system-skill houmao-utils-llm-wiki` to add one utility skill.

## Migration Plan

1. Add the policy parser/resolver and shared validation against the packaged system-skill catalog.
2. Add the project catalog schema column for launch-profile system-skill payloads with `{}` as the default.
3. Extend specialist recipe rendering/parsing to support `launch.system_skills`.
4. Extend easy specialist/profile and explicit launch-profile CLI storage surfaces.
5. Extend launch resolution and `BuildRequest` to carry source/profile policies into `BrainBuilder`.
6. Replace managed launch fixed install with resolved sync behavior.
7. Add manifest/runtime provenance and inspection output.
8. Update docs and tests.

Rollback is data-oriented: clear profile system-skill payloads, remove `launch.system_skills` from generated recipes, and rebuild managed homes with the default policy.

## Open Questions

- Should low-level `project agents recipes add/set` get explicit `--system-skill*` flags in this first change, or is YAML/manual recipe support sufficient while easy specialists own the primary baseline UI?
- Should `brains build` expose direct one-shot system-skill override flags for standalone build workflows, or should it only honor stored recipe/profile policy for now?
