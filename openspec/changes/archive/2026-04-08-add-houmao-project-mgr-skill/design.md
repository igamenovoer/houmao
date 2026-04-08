## Context

Houmao's packaged system-skill inventory already covers specialists, credentials, low-level agent definitions, generic managed-agent lifecycle, messaging, gateway control, and mailbox administration. The live `houmao-mgr project` surface has grown beyond that inventory: it now owns overlay initialization and status, catalog-backed project layout, explicit recipe-backed launch profiles, and project-scoped easy-instance inspection and stop flows. The renamed packaged skill family is already in place, so any new project skill needs to use the current `houmao-*-mgr` and `houmao-agent-*` identifiers rather than the retired `houmao-manage-*` names.

This change is cross-cutting even though it does not alter the underlying `project` CLI behavior. It adds one packaged skill, expands the `user-control` named set, changes the install-time inventory exposed by `houmao-mgr system-skills`, and updates README plus narrative/reference docs to explain the new project-management surface and its boundaries.

## Goals / Non-Goals

**Goals:**

- Add one packaged `houmao-project-mgr` skill that gives agents a canonical entrypoint for project overlay lifecycle, `.houmao/` layout, project-aware command effects, explicit launch profiles, and project-scoped easy-instance inspection or stop.
- Keep current ownership boundaries crisp by routing specialist/profile authoring, auth CRUD, low-level role/recipe authoring, mailbox administration, and generic live-agent lifecycle to the existing renamed skills.
- Put the new skill in the existing `user-control` set so managed launch/join and explicit CLI-default installs pick it up automatically without introducing another install-selection concept.
- Align README, system-skills overview, and CLI reference language with the current ten-skill inventory and renamed skill names.

**Non-Goals:**

- Changing the runtime behavior of `houmao-mgr project`, overlay resolution, launch-profile storage, or easy-instance commands.
- Merging all `project` subcommands into one monolithic system skill.
- Introducing a new named system-skill set such as `project-control`.
- Reintroducing compatibility wording around retired `houmao-manage-*` identifiers.

## Decisions

### 1. Add `houmao-project-mgr` to `user-control` instead of creating a new set

`houmao-project-mgr` belongs with the other user-authored project-management skills because it explains project-local overlay lifecycle and project-scoped authoring/inspection surfaces. Adding it to `user-control` means managed launch/join and CLI-default installs inherit the new skill through the existing set wiring, which keeps installation behavior simple and predictable.

Alternative considered: create a dedicated `project-control` set. Rejected because it would add new packaging, default-selection, and documentation complexity for one project-facing skill without solving a real boundary problem.

### 2. Make `houmao-project-mgr` a project front door, not the owner of all `project` subcommands

The new skill will own the project surfaces that currently have no better packaged home: `project init`, `project status`, `project agents launch-profiles ...`, and `project easy instance list|get|stop`. It will explicitly route neighboring concerns to the renamed specialist skills:

- `houmao-specialist-mgr` for easy specialist/profile authoring plus easy `launch|stop`
- `houmao-credential-mgr` for auth bundles
- `houmao-agent-definition` for roles and recipes
- `houmao-agent-instance` for generic lifecycle after project-scoped routing
- `houmao-mailbox-mgr` for mailbox administration

Alternative considered: document every `project` subcommand inside `houmao-project-mgr`. Rejected because that would duplicate other packaged skills, blur ownership boundaries, and make future maintenance harder.

### 3. Treat overlay resolution, layout, and project-aware effects as first-class reference material inside the skill

The skill needs more than a thin top-level `SKILL.md`. It should include focused references for overlay resolution, `.houmao/` layout, and project-aware effects on other command families. That lets the skill answer the user's core questions directly: how project files are organized and what happens to other subcommands once a project exists.

Alternative considered: keep all of that material inline in one long `SKILL.md`. Rejected because the resulting skill would be too dense, harder to cross-link, and harder to keep aligned with `agent-definitions.md`, `quickstart.md`, and `project-aware-operations.md`.

### 4. Preserve the current bootstrap distinction instead of flattening it away

The skill and docs should describe the actual behavior split that exists today:

- `project status` uses non-creating resolution and reports `would_bootstrap_overlay`
- stateful project-aware flows may ensure and bootstrap the selected overlay
- `project easy instance list|get|stop` use non-creating selected-overlay resolution and fail if no overlay exists yet

Alternative considered: describe all project commands as if they bootstrap an overlay automatically. Rejected because it would be inaccurate and would mislead operators about why project-scoped instance inspection fails before initialization.

## Risks / Trade-offs

- `[Expanded managed installs]` Adding `houmao-project-mgr` to `user-control` means managed homes and CLI-default installs gain another packaged skill. → Mitigation: keep the new skill tightly scoped to project lifecycle/layout/routing and document that it reuses existing renamed skills for neighboring workflows.
- `[Boundary overlap]` `houmao-project-mgr`, `houmao-specialist-mgr`, and `houmao-agent-instance` all touch project or instance concepts. → Mitigation: make the routing boundaries explicit in specs, skill docs, and the system-skills reference.
- `[Doc drift]` The narrative and reference docs already enumerate current skill counts and default installs, so adding a tenth skill can leave stale numbers behind. → Mitigation: update README, overview, and CLI reference requirements together in the same change.
- `[Behavior/documentation mismatch]` The bootstrap distinction is subtle and easy to oversimplify. → Mitigation: anchor the new skill docs to the live command behavior and retain the non-creating versus ensuring terminology in the references.

## Migration Plan

1. Add the new `houmao-project-mgr` packaged skill tree and wire it into `catalog.toml`.
2. Expand the `user-control` set so managed launch/join installs and CLI-default installs pick up the new skill automatically.
3. Update `houmao-mgr system-skills` inventory/reporting tests or snapshots to reflect the ten-skill packaged inventory and expanded `user-control` set.
4. Update README, system-skills overview, and CLI reference content to describe the new skill and the renamed-skill boundaries.

No runtime data migration is required because this change only adds packaged assets and catalog membership. Rollback is straightforward: remove the packaged skill and revert the catalog/doc updates.

## Open Questions

None. The two user-facing policy choices that were still open during exploration are now fixed for this change: `houmao-project-mgr` joins `user-control`, and all cross-skill references use the current renamed identifiers.
