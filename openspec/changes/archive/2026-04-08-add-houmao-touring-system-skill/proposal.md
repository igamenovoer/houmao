## Why

Houmao's current system skills expose the right direct-operation surfaces, but first-time users still have to discover the workflow boundaries themselves across project setup, mailbox setup, specialist creation, launch, live-agent operations, and lifecycle management. We need one manual-only guided touring skill that can orient new users from current state, explain the next meaningful branch with examples, and route them through the maintained Houmao skill surfaces without turning into a linear wizard.

## What Changes

- Add a new packaged Houmao-owned system skill named `houmao-touring`.
- Define `houmao-touring` as a manual-invocation-only, state-aware guided tour for first-time users rather than a direct-operation skill or one-shot onboarding wizard.
- Make the touring flow branchable and resumable so it can start from current project state, revisit earlier branches, and return to create more specialists or launch more agents after initial setup.
- Require the touring skill to cover project overlay setup, project mailbox setup, specialist/profile authoring entry, easy-instance launch, managed-agent prompting, gateway state watching, mailbox send/read entry, reminders, and managed-agent stop, relaunch, and cleanup entry.
- Require the touring skill to ask informative user-input questions with short explanations, realistic examples, and recommended defaults or skip options when appropriate.
- Add `houmao-touring` to the packaged system-skill inventory, flat projection/install surfaces, and the system-skills documentation inventory.
- Add a dedicated touring skill set so the packaged catalog can expose the touring skill without folding it into a direct-operation family.

## Capabilities

### New Capabilities
- `houmao-touring-skill`: Guided, manual-only first-user touring skill that composes existing Houmao system skills across setup, launch, live operations, and lifecycle follow-up.

### Modified Capabilities
- `houmao-system-skill-installation`: Add `houmao-touring` to the packaged system-skill inventory and packaged catalog selection model.
- `houmao-system-skill-families`: Add the touring skill as a flat packaged skill that can coexist with the other logical system-skill groups.
- `houmao-mgr-system-skills-cli`: Surface `houmao-touring` and its named set through `system-skills list|install|status`.
- `docs-system-skills-overview-guide`: Document `houmao-touring` as the manual guided tour skill in the narrative system-skills guide.
- `docs-readme-system-skills`: Add `houmao-touring` to the README system-skills catalog and explain that it is an explicit guided-tour entrypoint for first-time users.

## Impact

- Affected assets: `src/houmao/agents/assets/system_skills/`, especially the packaged catalog, new `houmao-touring/` tree, and installer-visible metadata.
- Affected code/tests: system-skill catalog loading and projection expectations in `src/houmao/agents/system_skills.py` and `tests/unit/agents/test_system_skills.py`.
- Affected docs: README system-skills catalog plus the system-skills overview and CLI-reference documentation.
