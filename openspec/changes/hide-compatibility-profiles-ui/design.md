## Context

`compatibility-profiles/` exists in three different layers today:

- as an optional `.houmao/agents/compatibility-profiles/` project-overlay subtree exposed by `houmao-mgr project init --with-compatibility-profiles`
- as a documented optional directory in getting-started, CLI reference, fixture, and system-skill guidance
- as internal profile-shaped runtime data used by the remaining CAO-compatible server/control path

Only the first two are operator-facing authoring surfaces. The maintained project model now uses catalog/content storage plus native roles, recipes, tools, skills, launch profiles, and mailbox configuration. CAO compatibility is a transition path, so compatibility-profile authoring should disappear from user interfaces before the larger CAO route/runtime retirement happens.

## Goals / Non-Goals

**Goals:**

- Remove the public `project init --with-compatibility-profiles` option rather than hiding it behind help text.
- Remove compatibility-profile authoring and layout mentions from maintained user docs, CLI reference, and packaged project-management skill guidance.
- Update the canonical tracked agent-definition tree contract so `compatibility-profiles/` is not part of the supported live layout.
- Preserve non-destructive behavior for existing local overlays that already contain `.houmao/agents/compatibility-profiles/`.
- Keep internal compatibility-profile-shaped source objects and launch-scoped sidecar generation where they still reduce implementation churn.

**Non-Goals:**

- Retiring `/cao/*` HTTP routes, `houmao_server_rest`, CAO-compatible clients, or provider adapters.
- Renaming internal classes such as `CompatibilityAgentProfile`.
- Deleting existing user-created `compatibility-profiles/` directories from disk.
- Maintaining backward compatibility for the removed public `--with-compatibility-profiles` flag.

## Decisions

### Decision 1: Remove the public flag instead of making it hidden

`houmao-mgr project init --with-compatibility-profiles` will be removed from the Click surface. Passing the flag after this change should fail as an unknown option.

Rationale:

- The project is explicitly allowed to make breaking changes during active development.
- A hidden accepted flag is still a public behavior surface and keeps an obsolete workflow alive.
- Failing clearly is easier to test and less ambiguous than silently ignoring the flag.

Alternative considered: keep a hidden Click option that still calls the existing internal bootstrap path. Rejected because it still teaches scripts that compatibility-profile bootstrap is a supported action.

### Decision 2: Keep internal bootstrap helpers only if they are not operator-reachable

The lower-level `include_compatibility_profiles` parameter and directory-creation helper may remain temporarily if removing them would cause broad churn, but no maintained CLI, docs, or skill should route users to it. Tests should stop asserting that the public CLI can create the subtree.

Rationale:

- The immediate target is user-interface removal.
- Internal helpers can be removed later with the broader CAO retirement or a focused cleanup once dependent tests/fixtures are gone.

Alternative considered: delete every internal path in one change. Rejected because source-level cleanup is broader than the user-facing design goal and risks entangling this work with CAO runtime retirement.

### Decision 3: Existing local directories are inert and non-destructively tolerated

If an existing overlay already contains `.houmao/agents/compatibility-profiles/`, project commands will leave it alone. They should not advertise, inspect, mutate, or delete it as part of normal project operation.

Rationale:

- Removing unexpected local files during project init or status would be hostile.
- Leaving the directory inert keeps the change focused and avoids migration machinery for obsolete local state.

Alternative considered: delete the directory during `project init`. Rejected because project init currently validates and preserves local payload state, and destructive cleanup should be explicit.

### Decision 4: Supported agent-definition layout excludes compatibility profiles

Maintained tracked agent-definition trees should no longer document or rely on a `compatibility-profiles/` directory. If any compatibility-only profile fixture is still needed for internal tests, move it to a test-only internal fixture location or inline it in the relevant test so it no longer appears as part of the canonical live tree.

Rationale:

- Keeping `tests/fixtures/plain-agent-def/compatibility-profiles/` under the canonical fixture tree weakens the new contract.
- Test-only compatibility artifacts can remain, but their path should make their internal status explicit.

Alternative considered: keep the fixture in place and only remove docs. Rejected because the fixture tree is used as a reference for supported tracked layout.

### Decision 5: CAO runtime retirement remains a separate track

This change should not remove `/cao/*` routes, CAO-compatible client parsing, server control-core provider adapters, or runtime profile-shaped projections. It should, however, avoid presenting compatibility profiles as user-authored state for those internals.

Rationale:

- The profile-shaped projection is currently an implementation detail used by remaining provider startup seams.
- Removing CAO compatibility is larger than hiding `compatibility-profiles/` and will require its own route, client, backend, test, and docs plan.

Alternative considered: fold CAO route retirement into this change. Rejected because it would obscure the smaller compatibility-profile authoring cleanup and produce a much larger blast radius.

## Risks / Trade-offs

- [Risk] Existing automation may still pass `--with-compatibility-profiles`. → Mitigation: make the failure explicit through Click's unknown-option behavior and remove the flag from all maintained docs/skills.
- [Risk] Internal compatibility-profile terminology remains in code and may look inconsistent. → Mitigation: accept source-level terminology until CAO runtime retirement; user-facing surfaces are the priority for this change.
- [Risk] Generated CLI reference or docs can drift if updated manually. → Mitigation: update both source docs and generated/reference outputs in the same implementation task, then grep for public `compatibility-profiles` references.
- [Risk] Moving test fixtures can accidentally break unrelated smoke flows. → Mitigation: verify fixture consumers and keep the `server-api-smoke` native role/preset path intact while relocating only obsolete Markdown compatibility-profile material.

## Migration Plan

1. Remove the public `--with-compatibility-profiles` Click option from `project init`.
2. Keep or prune internal overlay helpers based on local test impact, but ensure no supported CLI invokes compatibility-profile creation.
3. Update user docs, CLI reference docs, and `houmao-project-mgr` skill assets to remove all compatibility-profile bootstrap/layout guidance.
4. Update or relocate tracked compatibility-profile fixtures so supported live fixture trees no longer include that directory.
5. Update tests to assert the flag is absent/fails and that default init still does not create compatibility-profile state.
6. Run focused unit tests for project overlay, project CLI, system skills, and relevant fixture consumers; run docs/reference grep checks for stale public mentions.

Rollback is straightforward: restore the Click option, docs, skill guidance, and the previous project-init tests. No data migration is needed because the implementation does not delete existing local directories.

## Open Questions

None for this scoped cleanup. Full CAO compatibility retirement needs a separate proposal.
