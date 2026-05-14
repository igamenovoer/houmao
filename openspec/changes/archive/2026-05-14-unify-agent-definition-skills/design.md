## Context

Houmao has two adjacent persisted-agent-definition skills today:

- `houmao-agent-definition` covers low-level project-local roles and recipes.
- `houmao-specialist-mgr` covers project-easy specialists, easy profiles, and easy launch/stop entry points.

The product model has converged around easy profiles as the preferred operator-facing path, while low-level roles, recipes, and explicit recipe-backed launch profiles remain advanced building blocks. The current skill split makes agents ask routing questions even when the user just wants "create an agent" or "prepare a profile", and issue #52 asks for a one-click path that produces a ready-to-launch managed-agent profile from a specialist.

There is also a third ownership edge: `houmao-project-mgr` currently owns explicit recipe-backed launch-profile guidance because the command lives under `project agents launch-profiles`. Conceptually, that surface is still agent-definition/profile authoring, not project overlay lifecycle.

## Goals / Non-Goals

**Goals:**

- Make `houmao-agent-definition` the canonical packaged skill for persisted pre-launch agent definitions.
- Preserve clear lanes for low-level roles/recipes, explicit launch profiles, easy specialists, easy profiles, ready-profile generation, and limited easy launch/stop.
- Add a one-click ready-profile workflow that creates/selects a specialist, creates an easy profile, stores launch defaults, and prints the launch command without launching.
- Prefer easy profiles for normal agent creation and profile preparation.
- Keep existing dedicated skills authoritative for credentials, mailbox administration, workspace setup, and broad live-agent lifecycle.
- Provide a migration path for existing `houmao-specialist-mgr` references.

**Non-Goals:**

- Do not merge `houmao-credential-mgr`, `houmao-mailbox-mgr`, `houmao-agent-instance`, or `houmao-utils-workspace-mgr` into the unified skill.
- Do not change the underlying `houmao-mgr project easy ...`, `project agents roles ...`, `project agents recipes ...`, or `project agents launch-profiles ...` CLI command behavior in this change unless needed for documentation consistency.
- Do not make the one-click ready-profile path launch live agents by default.
- Do not require backwards-compatible behavior for every old skill identifier forever.

## Decisions

### Canonical Skill Name

Use `houmao-agent-definition` as the single canonical skill name.

Rationale: "agent definition" best covers the full pre-launch persisted identity stack: role, recipe, specialist, launch profile, easy profile, prompt material, skill bindings, birth-time defaults, and launch command shape. `houmao-specialist-mgr` is narrower and makes low-level and easy paths look unrelated.

Alternative considered: create a new `houmao-agent-profile-mgr` skill. This would avoid overloading the existing name, but it would add a third skill identifier and require more install/documentation churn.

### Internal Skill Shape

Use routed subskills rather than one long entry page:

```text
houmao-agent-definition/
  SKILL.md
  subskills/
    common/
      launcher.md
      missing-inputs.md
      profile-lanes.md
      credential-routing.md
    low-level/
      roles.md
      recipes.md
      launch-profiles.md
    easy/
      specialists.md
      profiles.md
      create-ready-agent-profile.md
      launch-instance.md
      stop-instance.md
  references/
    credentials/
      claude-kinds.md
      codex-kinds.md
      gemini-kinds.md
      claude-lookup.md
      codex-lookup.md
      gemini-lookup.md
```

Rationale: the existing skills already use action pages; keeping lanes separated avoids a large router page and lets agents load only the relevant command family.

Alternative considered: move the old `houmao-specialist-mgr/actions/*` files unchanged under `houmao-agent-definition/actions/`. That is simpler mechanically, but it preserves the current conceptual blur between specialists, easy profiles, explicit launch profiles, and live instances.

### Lane Model

Document the persisted definition lanes explicitly:

```text
low-level lane:
  role -> recipe -> explicit recipe-backed launch profile -> agents launch

easy lane:
  specialist -> easy profile -> project easy instance launch
```

Rationale: this gives agents a stable routing model and makes easy profiles the normal operator-facing path while preserving advanced low-level authoring.

### Ready-Profile Workflow

Add `easy/create-ready-agent-profile.md` as the one-click path.

The workflow creates or selects a specialist, creates or updates an easy profile, stores launch defaults, and reports:

- specialist name;
- easy profile name;
- stored defaults such as agent name/id, workdir, prompt mode, mailbox, gateway, notifier appendix, memo seed, model, reasoning, and env when supplied;
- exact launch command, normally `houmao-mgr project easy instance launch --profile <profile>`.

It does not launch the agent.

Rationale: a reusable easy profile is the durable artifact needed by loop `prepare-agents`, manual operators, and later launch commands. Launching immediately would mix definition authoring with runtime lifecycle.

Alternative considered: make one-click creation launch immediately. That would satisfy a narrow "make me an agent now" request but would be worse for loop preparation and reproducible profile defaults.

### Compatibility Wrapper

Keep `houmao-specialist-mgr` as a compatibility wrapper for one migration window when practical. Its entry page should route to the corresponding `houmao-agent-definition` easy subskill and state that `houmao-agent-definition` is canonical.

Rationale: repository docs, archived specs, installed homes, and users may still reference `houmao-specialist-mgr`. A redirect wrapper is cheap and reduces breakage.

Alternative considered: remove `houmao-specialist-mgr` immediately from packaged assets. This is acceptable in principle because the project tolerates breaking changes, but it creates avoidable install/status and documentation churn.

### Project Manager Boundary

Move explicit recipe-backed launch-profile authoring guidance from `houmao-project-mgr` to `houmao-agent-definition`.

`houmao-project-mgr` should still explain project overlay lifecycle, overlay resolution, `.houmao/` layout, project-aware side effects, and project-scoped easy-instance list/get/stop if those remain project-overlay inspection surfaces.

Rationale: explicit launch profiles are persisted agent-definition artifacts. Their command path starts with `project`, but their ownership is closer to roles, recipes, specialists, and easy profiles.

## Risks / Trade-offs

- [Risk] Existing installed homes still expose `houmao-specialist-mgr` and users invoke it directly. → Mitigation: keep a compatibility wrapper or document explicit migration if the wrapper is removed.
- [Risk] The unified entry page becomes too large. → Mitigation: keep `SKILL.md` as a concise router and move behavior into subskills/references.
- [Risk] Agents confuse explicit launch profiles with easy profiles because both are "profiles". → Mitigation: add a `profile-lanes.md` reference and require route decisions to use lane names: explicit recipe-backed launch profile vs specialist-backed easy profile.
- [Risk] One-click ready-profile guidance duplicates credential and mailbox mechanics. → Mitigation: route credential CRUD to `houmao-credential-mgr`, rely on easy specialist credential-source references for creation, and describe mailbox/gateway fields only as easy-profile defaults.
- [Risk] Moving explicit launch-profile ownership out of `houmao-project-mgr` leaves stale routing references. → Mitigation: update project-manager skill, docs, CLI reference, and specs together.

## Migration Plan

1. Build the expanded `houmao-agent-definition` structure with common, low-level, and easy subskills.
2. Move specialist/easy-profile action guidance and credential references into the unified skill.
3. Add `create-ready-agent-profile.md` and wire the top-level router to select it for "create an agent", "one-click agent", or "ready-to-launch profile" requests.
4. Move explicit recipe-backed launch-profile guidance from `houmao-project-mgr` into the unified skill and update `houmao-project-mgr` to route those requests onward.
5. Replace `houmao-specialist-mgr` with a compatibility wrapper or remove it from current install sets if the implementation chooses a hard break.
6. Update packaged system-skill catalog, install/status expectations, project/credential/loop routing references, README, getting-started docs, and CLI reference docs.
7. Validate system-skill packaging and OpenSpec specs before archiving.

Rollback is straightforward because this change primarily moves packaged skill guidance and docs: restore the previous two-skill assets and catalog membership if the unified router proves confusing.

## Open Questions

- Should `houmao-specialist-mgr` remain installable as an explicit compatibility skill, or should it be removed from install sets and only documented as obsolete?
- Should `project easy instance stop` stay on the unified definition skill as a narrow easy-workflow convenience, or should all stop flows move fully to `houmao-agent-instance` / `houmao-project-mgr`?
- Should the one-click ready-profile path support "update existing ready profile" as a patch operation in the first implementation, or only creation/replacement?
