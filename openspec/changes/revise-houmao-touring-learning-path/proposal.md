## Why

`houmao-touring` is meant to guide first-time and re-orienting users, but its current shape mixes first-run learning with broad capability discovery. Revising it into beginner, intermediate, and advanced learning stages will make the tour easier to follow while still routing users to the right owning skills as their Houmao use becomes more sophisticated.

## What Changes

- Reframe `houmao-touring` as a staged learning path rather than a broad Houmao function catalog.
- Add three explicit touring stages:
  - beginner: basic agent creation and communication, including tool selection, credentials, specialists, easy launch profiles, mailbox basics, launch, and direct conversation with an agent.
  - intermediate: post-launch operation and manual coordination, including memo usage, inter-agent messaging modes, prompt injection through mail, gateway/mail-notifier behavior, notifier-round mail processing, and agent inspection.
  - advanced: composed multi-agent systems, including loop-lite, loop-pro tree/generic loops, and isolated multi-agent workspace management.
- Revise next touring actions so branch follow-up suggestions are stage-aware instead of generic capability enumeration.
- Remove stale pairwise/generic retired-loop guidance from the touring requirements and keep current loop guidance on `houmao-agent-loop-lite` and `houmao-agent-loop-pro`.
- Preserve the tour's execution boundary: `houmao-touring` explains and routes; owning skills still perform project, credential, definition, mailbox, messaging, gateway, memory, loop, workspace, and lifecycle work.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-touring-skill`: revise the packaged touring skill contract from a branch catalog into a three-stage first-user learning path with stage-aware next actions and current loop/workspace routing.

## Impact

- Affected packaged skill content under `src/houmao/agents/assets/system_skills/houmao-touring/`.
- Affected OpenSpec contract in `openspec/specs/houmao-touring-skill/spec.md`.
- Possible documentation follow-up for system-skills overview or README wording if implementation changes public touring descriptions.
- No CLI command surface, runtime dependency, or storage-format changes are expected.
