## Why

Several mailbox-driven demos and prompt surfaces still behave as if Houmao runtime-owned mailbox skills are project content or skill-document paths. That breaks the intended contract: mailbox skills belong in tool-native runtime homes, and agents should be told to invoke them natively by skill name or tool-native trigger rather than by opening `SKILL.md` paths from the copied project.

This needs to be corrected now because the current mixed contract hides real regressions, lets supported demos succeed for the wrong reason, and leaves archived legacy demos advertising a workflow the maintained runtime no longer supports.

## What Changes

- Remove project-workdir mirroring of runtime-owned mailbox skills from supported demo flows.
- Update supported mailbox wake-up prompts and verification logic to depend on installed runtime-home mailbox skills and tool-native invocation behavior rather than `skills/.../SKILL.md` paths.
- Broaden the maintained native-skill contract in supported demos so Claude, Codex, and Gemini lanes all rely on installed Houmao mailbox skills without project-local mirrors.
- Block legacy demo entry points that still depend on project-local mailbox skill copies or path-based skill prompting, and fail with a clear explanation that those demos are archived because of the invalid contract.
- Update reference documentation so it describes runtime-home mailbox skill projection and native invocation guidance rather than path-oriented prompt substitution.

## Capabilities

### New Capabilities
- `legacy-demo-entrypoint-guards`: archived demos with deprecated project-local mailbox-skill contracts fail fast with a clear explanation instead of running.

### Modified Capabilities
- `agent-mailbox-system-skills`: runtime-owned mailbox skills remain runtime-home assets only and ordinary prompting relies on native tool invocation rather than project-local copies or skill-document paths.
- `agent-gateway-mail-notifier`: notifier wake-up prompts use native installed-skill guidance and never surface `skills/.../SKILL.md` paths as the operational contract.
- `single-agent-mail-wakeup-demo`: the supported TUI wake-up demo relies on runtime-home mailbox skills, verifies the runtime skill surface, and does not copy mailbox skills into the copied project.
- `single-agent-gateway-wakeup-headless-demo`: the supported headless wake-up demo requires native installed-skill invocation for all maintained lanes and does not rely on project-local mailbox-skill mirrors.
- `docs-gateway-mail-notifier-reference`: the gateway notifier reference documents native mailbox-skill invocation guidance instead of path-based skill-document wording.
- `docs-project-mailbox-skills`: the mailbox skills reference documents runtime-home projection only and explicitly states that copied project content is not part of the mailbox-skill contract.

## Impact

- Affected code: mailbox skill projection and prompt construction, supported demo runtime/reporting layers, archived legacy demo CLI entry points, and mailbox/gateway reference docs.
- Affected systems: Claude Code, Codex, and Gemini mailbox wake-up flows; demo verification logic; archived demo operator experience.
- Breaking behavior: archived legacy demo entry points that still depend on deprecated project-local mailbox-skill mirroring will stop running and will return a clear explanatory error instead.
