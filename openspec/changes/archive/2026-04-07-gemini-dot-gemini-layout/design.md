## Context

Houmao currently treats Gemini differently from its own setup and auth layout. The Gemini tool adapter projects setup files into `.gemini/`, but selected skills and Houmao-owned system skills still project into `.agents/skills/`. That split is now part of the maintained runtime, mailbox-skill, and `system-skills` CLI contract.

This is a cross-cutting path contract problem rather than one isolated adapter bug:

- managed brain construction uses the adapter-defined Gemini skill destination,
- runtime-owned mailbox skill helpers inherit the Gemini visible skill root,
- `houmao-mgr system-skills` hardcodes Gemini system-skill projection to `.agents/skills`,
- documentation and tests encode `.agents/skills` as the maintained Gemini path.

Upstream Gemini CLI already treats `.gemini/skills` as the native workspace skill root and only scans `.agents/skills` as an alias surface. Keeping Houmao on `.agents/skills` therefore leaks Gemini-managed Houmao skills into a generic alias that other tools can discover and makes stale alias content more likely to override the intended `.gemini` content.

## Goals / Non-Goals

**Goals:**

- Make `.gemini/skills` the single maintained visible Gemini skill root for Houmao-managed content.
- Keep Gemini home-root resolution unchanged: `GEMINI_CLI_HOME` and omitted-home Gemini flows still resolve the home root itself, not the `.gemini` subdirectory.
- Cover both managed runtime projection and `houmao-mgr system-skills`.
- Migrate previously Houmao-owned Gemini system-skill installs away from `.agents/skills`.
- Stop leaving `.agents/skills` as active Houmao-managed content inside reused managed Gemini homes.

**Non-Goals:**

- Changing Gemini auth file semantics or moving Gemini auth material out of `.gemini/`.
- Changing upstream Gemini CLI alias behavior or trying to manage third-party `.agents/skills` content outside Houmao ownership.
- Broadly refactoring unrelated Gemini runtime naming inconsistencies unless they are required to complete this path-contract change.

## Decisions

### 1. Keep the Gemini home root unchanged and move only the managed skill destination

Gemini will keep the existing home-root contract:

- explicit `--home` or `GEMINI_CLI_HOME` selects the Gemini home root,
- omitted-home `houmao-mgr system-skills --tool gemini` still uses `<cwd>` as the effective home root,
- visible managed skill content under that home now lives at `<home>/.gemini/skills/`.

This matches upstream Gemini CLI semantics, which derive `.gemini/...` paths from the home root selected by `GEMINI_CLI_HOME`.

Alternative considered:

- Treat `<home>/.gemini` as the effective home for Houmao CLI surfaces. Rejected because it would diverge from Gemini CLI's own home-root contract and make Houmao's `--home` behavior provider-specific in a confusing way.

### 2. Do not dual-write or mirror Houmao-managed Gemini skills into `.agents/skills`

Houmao will switch the maintained Gemini skill destination to `.gemini/skills` and will not keep `.agents/skills` as a compatibility mirror for Houmao-managed content.

This avoids the exact problem that motivated the change: generic `.agents` discovery by other tools. It also avoids alias-precedence ambiguity when both `.gemini/skills` and `.agents/skills` contain the same skill name.

Alternative considered:

- Write both `.gemini/skills` and `.agents/skills` during a transition period. Rejected because it preserves cross-tool leakage and keeps stale alias content live in the same workspace.

### 3. Use two migration paths: installer-owned cleanup for system skills, builder-owned cleanup for managed homes

For Houmao-owned system skills, migration will rely on existing installer ownership tracking:

- Gemini system-skill destination changes from `.agents/skills/<skill>` to `.gemini/skills/<skill>`.
- Reinstall and auto-install already know how to remove previously owned paths when the recorded owned path changes.

For selected non-system skills in managed Gemini homes, the builder needs separate cleanup because those projected skills are not tracked in system-skill install state. The managed-home build path will remove the legacy Houmao-managed `.agents/skills` content it previously created before or during projection into `.gemini/skills`, especially for `reuse_home` flows.

Alternative considered:

- Rely only on fresh-home creation and leave reuse-home migration unresolved. Rejected because stale `.agents/skills` content would remain visible in the exact managed homes that opt into reuse.

### 4. Mailbox runtime-owned Gemini skills follow the same `.gemini/skills` contract

Mailbox runtime helpers already derive the visible skill destination from shared system-skill destination logic. This change keeps one Gemini path contract across:

- selected managed skills,
- Houmao-owned system skills,
- runtime-owned mailbox skills,
- Gemini-facing mailbox prompting and docs.

Alternative considered:

- Move general Gemini skills to `.gemini/skills` but keep mailbox runtime skills under `.agents/skills`. Rejected because it would leave two maintained Gemini skill roots and repeat the current inconsistency in a narrower form.

## Risks / Trade-offs

- [Legacy non-owned `.agents/skills` content remains in externally managed homes] -> Mitigation: only automatically delete Houmao-owned Gemini system-skill paths recorded by install state, and limit managed-home cleanup to Houmao-managed runtime homes rather than arbitrary external Gemini homes.
- [Reuse-home cleanup could remove user-added files in Houmao-managed Gemini runtime homes] -> Mitigation: scope cleanup to the legacy Houmao-managed Gemini skill root and keep the migration focused on previously projected Houmao-managed content rather than broad filesystem pruning.
- [Docs and tests encode the old Gemini path in many places] -> Mitigation: treat docs and test updates as part of the same change rather than as follow-up cleanup.

## Migration Plan

1. Change the Gemini tool adapter skill destination to `.gemini/skills`.
2. Change shared Gemini system-skill destination constants from `.agents/skills` to `.gemini/skills`.
3. Keep Gemini effective-home resolution unchanged for CLI and managed runtime flows.
4. On Gemini system-skill reinstall or auto-install, rely on installer ownership tracking to remove previously owned `.agents/skills/<skill>` paths and record `.gemini/skills/<skill>` instead.
5. On managed Gemini home construction, remove the legacy Houmao-managed `.agents/skills` content before or during projection into `.gemini/skills`, including reuse-home flows.
6. Update mailbox skill helpers, tests, and docs to treat `.gemini/skills` as the only maintained Gemini skill root.

Rollback strategy:

- Revert the destination constants and adapter metadata to `.agents/skills`.
- Rebuild affected managed homes or reinstall Gemini system skills to repopulate the prior layout if rollback is required during development.

## Open Questions

None for this change. The unrelated `GEMINI_HOME` versus `GEMINI_CLI_HOME` naming cleanup can be evaluated separately after the managed skill-root contract is consistent.
