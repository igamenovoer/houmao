## Why

Houmao already exposes maintained mailbox administration surfaces for filesystem mailbox roots, project-local mailbox roots, and late managed-agent mailbox binding, but no packaged Houmao-owned system skill routes agents to those surfaces. That leaves mailbox bootstrap and mailbox lifecycle work split across CLI docs and other skills even though mailbox operations, notifier rounds, and gateway control already have first-class skill entrypoints.

## What Changes

- Add a new packaged Houmao-owned system skill named `houmao-mailbox-mgr` under the maintained system-skill asset root.
- Make `houmao-mailbox-mgr` the entrypoint for mailbox administration intent across:
  - `houmao-mgr mailbox ...` for arbitrary filesystem mailbox roots,
  - `houmao-mgr project mailbox ...` for overlay-local mailbox roots,
  - `houmao-mgr agents mailbox ...` for late filesystem mailbox binding on existing local managed agents.
- Structure the skill as one top-level `SKILL.md` router plus action pages for mailbox root bootstrap, status, registration lifecycle, repair, cleanup, account inspection, structural message inspection, and agent-binding lifecycle.
- Keep actor-scoped mailbox follow-up, gateway mail-notifier control, and ordinary `/v1/mail/*` work outside this skill so the existing mailbox, messaging, and gateway skills remain authoritative for those paths.
- Expand the packaged mailbox skill inventory so `mailbox-core` remains the worker pair while `mailbox-full` includes the new mailbox-admin skill.
- Update system-skills inventory/docs surfaces to include the new packaged skill and the revised mailbox set semantics.

## Capabilities

### New Capabilities
- `houmao-mailbox-mgr-skill`: packaged Houmao-owned skill for mailbox root administration, project mailbox administration, and late managed-agent mailbox binding.

### Modified Capabilities
- `houmao-system-skill-installation`: packaged skill inventory and named-set membership change to include `houmao-mailbox-mgr` and expand `mailbox-full`.
- `houmao-mgr-system-skills-cli`: list/install/status output and mailbox-set semantics change to report the new skill and distinguish `mailbox-core` from `mailbox-full`.
- `docs-cli-reference`: CLI reference coverage changes to document the new packaged skill and updated system-skills inventory/set behavior.
- `docs-system-skills-overview-guide`: narrative guide changes to include the new skill and updated mailbox auto-install/default-install grouping.
- `docs-readme-system-skills`: README system-skills subsection changes to include the new skill and reflect the updated packaged skill/default-set story.

## Impact

- Affected assets under `src/houmao/agents/assets/system_skills/`, especially the packaged catalog and a new `houmao-mailbox-mgr/` skill tree.
- Affected system-skills installation and inventory reporting through `houmao-mgr system-skills ...`.
- Affected operator-facing docs for system skills and mailbox-related packaged-skill boundaries.
- No new mailbox transport CLI is introduced in this change; filesystem mailbox admin and late filesystem binding remain the maintained command surfaces in v1, while Stalwart stays documented as a transport/bootstrap boundary rather than a peer mailbox-admin CLI family.
