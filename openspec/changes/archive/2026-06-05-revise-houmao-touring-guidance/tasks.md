## 1. Touring Entry and Coverage

- [x] 1.1 Update `src/houmao/agents/assets/system_skills/houmao-touring/SKILL.md` audience language to target users not yet familiar with Houmao, including first-run users, re-orienting operators, and developers inspecting system logic.
- [x] 1.2 Add an explicit entry contract that distinguishes help intent, orientation requests, outcome requests, and subsystem-exploration requests.
- [x] 1.3 Update help and common starting prompts to include fast path use cases and subsystem exploration without presenting a full skill catalog.
- [x] 1.4 Update workflow ordering so current-state inspection happens before state-adaptive welcome selection.

## 2. Fast Path Use Cases

- [x] 2.1 Add packaged touring guidance for the three fast path use cases: Single Agent Full Run, Operator-Controlled Agent Team, and Pro Agent Loop.
- [x] 2.2 Ensure Single Agent Full Run includes project readiness, tool and credential readiness, specialist or profile setup, foreground-first launch, gateway, mailbox, notification, prompt, inspection, memory, and reminders as intended tour surfaces.
- [x] 2.3 Ensure Operator-Controlled Agent Team includes multiple fully functional agents, per-agent gateway and mailbox readiness, direct prompts, operator-origin mail, inter-agent mail, notifier setup, inspection, memory, reminders, and lifecycle follow-up.
- [x] 2.4 Ensure Pro Agent Loop routes generated loop construction through `houmao-agent-loop-pro` and presents `tree-loop` and `generic-loop` as topology modes inside pro.

## 3. Subsystem Exploration

- [x] 3.1 Add a packaged subsystem-exploration branch or equivalent self-contained touring content under `src/houmao/agents/assets/system_skills/houmao-touring/`.
- [x] 3.2 Present a compact subsystem map covering Project overlay, Agent definition, Managed runtime, Gateway, Messaging, Mailbox, Memory, Inspection, Workspace, and Loop orchestration.
- [x] 3.3 For each subsystem, define the boundary, required input, generated state, main operations, owning skill routes, and nearby next choices.
- [x] 3.4 Keep passive server, deeper TUI tracking behavior, raw command examples, and deeper architecture explanation behind `more detail` or explicit advanced-internals requests.

## 4. Presentation Style

- [x] 4.1 Update touring guidance so each completed step reports operation result, critical current status, brief next-step or branch choices, and required input when needed.
- [x] 4.2 Add compact-output guidance that avoids one rigid response template and avoids deep explanations by default.
- [x] 4.3 Prefer small Markdown tables for status, operation choices, and branch choices when clearer than lists, and state that tables should use at most four columns.
- [x] 4.4 Add `more detail` expansion behavior for command examples, raw evidence, fuller concept explanations, and deeper architecture detail.
- [x] 4.5 Add one or more presentation template examples inside the packaged skill or a loaded branch/subskill file, with concise wording and adaptable response shapes.
- [x] 4.6 Ensure presentation examples focus on user intent, operation result, current posture, next choices, and required input rather than command invocation syntax.
- [x] 4.7 Ensure touring guidance routes concrete work to owning skills where possible and avoids duplicating those skills' detailed workflows, command references, option catalogs, or validation rules.

## 5. Tests and Validation

- [x] 5.1 Update unit tests that assert packaged `houmao-touring` content to cover the two coverage lanes, the three fast path use cases, subsystem exploration, compact tables, presentation examples, routing-to-owning-skills guidance, and `more detail`.
- [x] 5.2 Validate no packaged touring content references development-only paths outside `src/houmao/agents/assets/system_skills/houmao-touring/`.
- [x] 5.3 Run focused tests for packaged system skill installation/content.
- [x] 5.4 Run `pixi run test` or document why the full unit suite was not run.

## 6. No-Prompt Entrypoint Refinement

- [x] 6.1 Update packaged `houmao-touring` guidance so bare `$houmao-touring` scans existing Houmao project state before presenting next steps.
- [x] 6.2 Add an intent-guess matrix based on inspected state, covering blank workspace, project-without-specialists, definitions-without-runtime, one running agent, multiple running agents, loop/topology hints, and component-minded wording.
- [x] 6.3 Ensure no-prompt output introduces Houmao in context and presents current posture, likely intent, next choices, and required input instead of an empty greeting.
- [x] 6.4 Update `agents/openai.yaml` so embedded agents do not stop at generic skill activation acknowledgement.
- [x] 6.5 Update tests to assert no-prompt scan, intent guess, contextual introduction, next choices, and anti-empty-greeting behavior.
