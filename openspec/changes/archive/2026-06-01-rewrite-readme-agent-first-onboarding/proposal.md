## Why

The current README says Houmao is agent-driven, but the Quick Start and usage sections quickly become a human-facing command tutorial. This buries Houmao's strongest advantage: a user can install Houmao skills into a CLI agent and then ask that agent to create, launch, inspect, message, and coordinate other managed agents.

## What Changes

- Rewrite README content from Quick Start onward around an agent-first onboarding story.
- Make the install path short: install Houmao with `uv`, verify `tmux`, install Houmao skills, then start a CLI agent and invoke `houmao-touring`.
- Prefer `npx skills add igamenovoer/tool-skills/houmao` for ordinary system-skill installation while still documenting `houmao-mgr system-skills install ...` as the fallback/custom/offline path.
- Replace command-heavy usage blocks with AI/user conversation examples in the style of the OpenSpec README.
- Introduce specialists, easy profiles, managed agents, gateways, and mailbox interaction through a simple workflow driven by the user's CLI agent.
- Elevate `houmao-agent-loop-pro` as the main "where Houmao shines" story: feed a complex multi-agent plan to the pro loop skill, let it decompose the work, prepare participants, and run the loop.
- Move detailed command syntax and full skill catalogs out of the README narrative and into linked docs/reference pages.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `readme-structure`: revise README onboarding order, installation emphasis, usage style, concept introduction, and loop positioning toward agent-first operation.

## Impact

- Affects `README.md`.
- May require small updates to README-structure tests or documentation guards that assert specific headings, command snippets, or skill-install wording.
- Does not change runtime behavior, CLI APIs, skill package contents, or generated agent assets.
