## Why

Recent system-skill changes introduced two user-facing shifts: the preferred install path can now be `npx skills add` against the GitHub main-branch `system_skills/` collection, and every current packaged Houmao system skill can answer explicit read-only help such as `$houmao-touring help`. The docs site still has entry points and reference pages that frame `houmao-mgr system-skills install` as the only first step or omit the skill-level help convention, so readers can miss the recommended workflow or confuse prompt-level help with a CLI subcommand.

## What Changes

- Update docs entry points so `npx skills add https://github.com/igamenovoer/houmao/tree/main/src/houmao/agents/assets/system_skills/` is presented as the recommended install path when `npx` and internet access are available.
- Keep `houmao-mgr system-skills install` documented as the package-local/offline/customizable path for named sets, subset skills, explicit homes, symlink/copy projection, and cleanup behavior.
- Update the docs index installed-user path so it no longer starts exclusively with `houmao-mgr system-skills install`.
- Expand the system-skills overview with an "Installation Choices" style section that compares `npx skills add` and `houmao-mgr system-skills install`, then points readers at skill-level help.
- Update the system-skills CLI reference to explain that it documents `houmao-mgr system-skills`, while prompt-level `$<skill> help` is answered by installed skills and is not a new CLI subcommand.
- Keep README guidance consistent with the docs site and update OpenSpec docs contracts so the current README text is no longer out of spec.
- Add focused docs tests or guards for the normalized install/help story.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `readme-structure`: Quick Start "Drive with Your CLI Agent" should present `npx skills add` as the recommended first install option when available, with `houmao-mgr system-skills install` as the offline/custom path.
- `docs-readme-system-skills`: README system-skill guidance should preserve the `npx` versus `houmao-mgr` distinction and the explicit read-only skill-help convention.
- `docs-system-skills-overview-guide`: The overview should explain installation choices, skill-level help, and the explicit-help versus ordinary workflow boundary.
- `docs-cli-reference`: The system-skills CLI reference should distinguish the operator-facing `houmao-mgr system-skills` surface from prompt-level installed-skill help and mention the external Skills CLI install option as adjacent guidance.
- `docs-site-structure`: The docs landing page should route installed users through the current recommended agent-driven install/help path.

## Impact

- Affected docs: `README.md`, `docs/index.md`, `docs/getting-started/system-skills-overview.md`, and `docs/reference/cli/system-skills.md`.
- Affected OpenSpec specs: docs-only delta specs for README, docs index/site structure, system-skills overview, and CLI reference coverage.
- Affected tests: focused docs guard tests covering install choice wording and skill-level help wording.
- No runtime API, CLI behavior, catalog schema, packaged skill asset, or migration is required.
