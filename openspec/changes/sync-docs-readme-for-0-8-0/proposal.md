## Why

The 0.8.0 release added user-visible capabilities — the `houmao-agent-loop-pairwise-v3` workspace-aware loop skill, lifecycle-aware managed-agent registry (active/stopped/relaunching/retired), `--reuse-home fresh` launch mode, gateway control-request coalescing, and mail-notifier context-recovery policy — that are already documented in their deep reference pages. The two places a new reader actually starts (`README.md` and `docs/index.md`) have not caught up: the README loop table still says three loop skills, the README system-skills table is missing `houmao-agent-loop-pairwise-v3`, and the docs index landing page does not surface the lifecycle-aware registry or gateway-coalescing/mail-notifier-policy additions from the subsystems block.

The cost of leaving this stale is that a 0.8.0 user has no discovery path to the new capabilities from the entry points, even though every underlying reference page is correct.

## What Changes

- Add a `houmao-agent-loop-pairwise-v3` row to the README `§4 Agent Loop` loop-skills table.
- Add a `houmao-agent-loop-pairwise-v3` row to the README "System Skills: Agent Self-Management" catalog table.
- Update the README `§4 Agent Loop` narrative count from three to four loop skills and keep the existing pairwise walkthrough intact as the canonical worked example.
- Update the README auto-install paragraph so the `user-control`/`core` expansion wording includes all three pairwise variants (`houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`) to match the current `catalog.toml`.
- Refresh the `docs/index.md` Subsystems block so Gateway, Mailbox, Agent Registry, and Run-phase links each surface the 0.8.0 capabilities through their existing reference pages (coalescing section, context-recovery-policy section, lifecycle-state record section, reuse-home / stop-relaunch section).
- No new getting-started pages, no new reference pages, no edits to already-synced pages (`loop-authoring.md`, `system-skills-overview.md`, `quickstart.md`, `easy-specialists.md`, `launch-profiles.md`, registry and gateway references).
- The README "See it in action" video block, story-writer example, and 0.7-era narrative around the video are retained unchanged.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `docs-readme-system-skills`: the README catalog and §4 loop-section requirements are extended to include `houmao-agent-loop-pairwise-v3` alongside the existing pairwise variants, and the auto-install wording is extended to cover the three-pairwise-variant `core`/`all` set from `src/houmao/agents/assets/system_skills/catalog.toml`.
- `docs-site-structure`: the `docs/index.md` subsystems coverage requirement is extended so Gateway, Mailbox/Mail-notifier, Agent Registry, and Run-phase entries surface the 0.8.0 anchors (`coalescing`, `mail-notifier context recovery`, `lifecycle-aware record`, `reuse-home / stop-relaunch`) rather than only top-level index pages.

## Impact

- Affected files: `README.md`, `docs/index.md` only.
- No code, no CLI, no schema, no migration, no tests.
- No consumer of `mkdocs.yml` navigation is affected — the site uses auto-nav and no files are added or renamed.
- All linked target pages (`docs/getting-started/loop-authoring.md`, `docs/getting-started/system-skills-overview.md`, `docs/reference/registry/contracts/record-and-layout.md`, `docs/reference/gateway/contracts/protocol-and-state.md`, `docs/reference/gateway/operations/mail-notifier.md`, `docs/reference/run-phase/session-lifecycle.md`) already exist and already carry the 0.8.0 content.
