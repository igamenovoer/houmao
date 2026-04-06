## Context

Houmao already has a maintained low-level auth-bundle CLI surface under `houmao-mgr project agents tools <tool> auth ...`, but the packaged Houmao-owned system-skill family does not yet include a matching skill that tells agents how to use that surface safely. The current packaged non-mailbox grouping is also named `project-easy`, even though the grouping now needs to cover more than easy-specialist authoring once low-level credential management is added.

The relevant current constraints are:

- packaged system skills are flat assets under `src/houmao/agents/assets/system_skills/`,
- named sets and auto-install defaults are driven from the packaged catalog,
- Claude, Codex, and Gemini all project those skills into tool-native visible roots,
- `project agents tools <tool> auth get` already provides safe redacted inspection, while `add|set|remove` mutate stored auth bundles directly,
- managed-launch and managed-join auto-install currently include the non-mailbox authoring set, while CLI-default additionally includes the separate agent-instance lifecycle set.

The change is cross-cutting because it touches packaged skill assets, catalog naming, auto-install selection, CLI reporting, tests, and user-facing docs.

## Goals / Non-Goals

**Goals:**

- Add a packaged `houmao-manage-credentials` skill that routes to the supported project-local auth-bundle CLI for Claude, Codex, and Gemini.
- Keep the user-provided skill name `houmao-manage-credentials`.
- Rename the packaged named set currently called `project-easy` to `user-control`.
- Add `houmao-manage-credentials` to the renamed `user-control` set so it installs alongside the other user-controlled-agent skills.
- Update packaged auto-install selection, CLI reporting, tests, and docs to use the renamed set and new skill consistently.

**Non-Goals:**

- Renaming the existing `houmao-mgr project easy ...` CLI surface.
- Renaming `houmao-manage-specialist` or `houmao-manage-agent-instance`.
- Changing the on-disk auth-bundle layout or the existing tool-specific auth CLI semantics.
- Adding interactive login generation, ambient credential discovery, or raw secret dumping to the new skill.
- Folding the separate `agent-instance` set into `user-control` in this change.

## Decisions

### Decision: Keep `houmao-manage-credentials` as the packaged skill name

The new packaged skill will use the exact user-requested name `houmao-manage-credentials`, even though the underlying CLI and docs use the more precise term `auth bundle`.

This keeps the public skill trigger stable and intuitive while still allowing the skill body to explain that the concrete Houmao primitive is a project-local tool-scoped auth bundle.

Alternative considered:

- `houmao-manage-auth-bundles`: more exact, but it rejects the user-requested public skill name and creates unnecessary churn in the packaged skill namespace.

### Decision: Rename the packaged named set `project-easy` to `user-control`

The named set will be renamed at the packaged catalog layer only. The `houmao-mgr project easy ...` command family stays unchanged.

This keeps the higher-level CLI stable while letting the packaged skill grouping describe its true install purpose: skills intended for user-controlled agents. The renamed set will contain:

- `houmao-manage-specialist`
- `houmao-manage-credentials`

Alternative considered:

- keep `project-easy` and add the new skill there: rejected because the set name would become misleading once it contains both high-level specialist authoring and low-level credential management guidance.

### Decision: Keep `agent-instance` as a separate named set

The new `user-control` set does not absorb `houmao-manage-agent-instance`. The packaged catalog will continue to model agent-instance lifecycle guidance as a distinct set.

This preserves the current distinction between:

- skills installed for user-controlled specialist and credential management, and
- the separate managed-agent lifecycle skill that is only added through CLI-default selection.

Alternative considered:

- fold `houmao-manage-agent-instance` into `user-control`: rejected because it would broaden managed-launch and managed-join auto-install behavior beyond the requested change.

### Decision: The new skill stays explicit-input oriented

`houmao-manage-credentials` will route agents to the documented per-tool `auth list|get|add|set|remove` commands and require explicit user-provided inputs for mutating actions.

The skill will not introduce automatic env scanning, home-dir scanning, or login discovery by default. For inspection it will rely on the existing redacted `auth get` output instead of reading raw secret files directly.

Alternative considered:

- reusing the specialist-create credential-discovery modes inside the new low-level auth skill: rejected because low-level auth mutation should remain deliberate and narrow, and the existing CLI already offers explicit per-tool mutation flags.

### Decision: Reuse the existing packaged skill structure

The new skill will follow the same packaged layout as the existing Houmao-owned routed skills:

- top-level `SKILL.md` as the router,
- `actions/*.md` for per-action guidance,
- `agents/openai.yaml` for the default prompt stub.

This keeps installer behavior, projected on-disk shape, and future maintenance uniform across the Houmao-owned skill family.

Alternative considered:

- embedding the whole workflow in one large `SKILL.md`: rejected because the existing routed-skill pattern is already established and easier to extend safely.

## Risks / Trade-offs

- [Breaking named-set rename] → Operators or tests that currently reference `--set project-easy` will need to move to `--set user-control`; docs and CLI reporting must make that rename explicit.
- [Broader managed auto-install contents] → Because `managed_launch_sets` and `managed_join_sets` will reference `user-control`, managed homes will now receive `houmao-manage-credentials` in addition to `houmao-manage-specialist`; the specs and tests must make that broadened selection intentional.
- [Terminology overlap with `project easy`] → The repo will temporarily have both the `project easy` CLI family and the `user-control` packaged set; docs must distinguish the command family from the packaged skill grouping clearly.
- [Tool-surface asymmetry] → The new skill must reflect real per-tool auth semantics, including cases where one tool supports fewer clear-style flags than another, rather than promising a fake symmetric interface.

## Migration Plan

1. Add the new packaged skill assets and register the skill in the packaged catalog.
2. Rename the named set from `project-easy` to `user-control` in packaged catalog data, installer constants, and any CLI-reporting fixtures.
3. Update fixed auto-install selections so managed-launch and managed-join reference `user-control`, while CLI-default continues to include both `user-control` and `agent-instance`.
4. Update tests and docs to use the renamed set and to expect `houmao-manage-credentials` in the relevant resolved install lists.
5. Treat `project-easy` as removed packaged-set vocabulary; callers that previously used `system-skills install --set project-easy` must switch to `--set user-control`.

No persisted data migration is required beyond normal reinstall or re-projection of Houmao-owned packaged skills.

## Open Questions

- None for this proposal. The requested public name, set placement, and set rename are all explicit.
