## Context

Houmao system skills are distributed as self-contained `SKILL.md` instruction packages under `src/houmao/agents/assets/system_skills/` and installed into Claude, Codex, Copilot, and Gemini skill homes. Most current skills already expose some combination of scope, workflow, routing, actions, operations, or supported surfaces, but there is no uniform meta operation that teaches an agent how to answer "what can this skill do?" without starting normal workflow execution.

This matters more now that users can install skills individually through external skill tooling. A skill installed outside the full Houmao catalog should still be able to explain its purpose, available functionality, and related skill boundaries from its own local files.

## Goals / Non-Goals

**Goals:**

- Add a standard read-only `help` operation to every current catalog system skill.
- Keep help local to each top-level `SKILL.md`, so every installed skill is self-describing.
- Make help responses useful to an agent or operator by listing purpose, available functionality, common starting prompts, and related skill boundaries.
- Ensure `help` is routed before mutating or input-gathering workflows.
- Keep legacy retired skill assets outside the requirement.
- Add focused tests that prevent future catalog skills from shipping without the help contract.

**Non-Goals:**

- Do not add a new `houmao-mgr` command.
- Do not change the packaged catalog schema or install resolution.
- Do not create generated help from code or from the catalog at runtime.
- Do not require retired legacy skills under `legacy/` to be updated.
- Do not make "help me do X" stop at usage text when the user clearly wants the actual workflow.

## Decisions

### 1. Help is a skill meta operation, not a CLI command

Each current skill will handle help in its own `SKILL.md`. This matches how users invoke installed skills and avoids making a full Houmao runtime or catalog lookup a prerequisite for understanding a single installed skill.

Alternative considered: add `houmao-mgr system-skills help <skill>`. Rejected because it would only help operators with the CLI available and would not help an agent reading an individually installed skill.

### 2. Help must be explicit and read-only

The trigger should be narrow: `<skill-name> help`, "usage for this skill", "available functionality", or "what can this skill do?". Help responses do not run commands, mutate files, ask missing-input questions, or choose action pages. They explain and stop.

This prevents accidental mutation when the user is only exploring a skill. It also avoids blocking real tasks such as "help me send mail" or "help me launch an agent"; those should still route to normal workflows.

### 3. Top-level `SKILL.md` owns the help summary

The help section belongs near the top-level routing material, not buried in action pages. Skills with operations can list `help` in `## Operations`; router-style skills can add a `## Help` section plus a first workflow step that handles help before routing.

Alternative considered: put help in a shared reference file and link to it from every skill. Rejected because help text needs skill-specific functionality and boundary summaries, and a single installed skill should not depend on other skill packages.

### 4. Tests enforce shape, not exact prose

Tests should verify every current catalog skill has a `## Help` section and contains key contract phrases such as read-only behavior, available functionality, common starting prompts, and related skills or boundaries. Exact formatting can vary by skill because the available functionality differs.

## Risks / Trade-offs

- [Help text drifts from actual skill routes] -> Keep help summaries short and derive them from existing operation/action lists during implementation.
- [Help trigger becomes too broad] -> Require explicit help/usage intent and preserve normal routing for task-shaped prompts.
- [Updating every skill creates repetitive text] -> Use a standard compact structure but tailor available functionality per skill.
- [Individual skill help omits related-skill boundaries] -> Require every help section to name either related skills or out-of-scope handoffs where applicable.

## Migration Plan

1. Update all current catalog top-level `SKILL.md` files with a standard `## Help` section.
2. Add routing language so explicit help intent is answered before normal workflow, branch, operation, or action routing.
3. Update README and the system-skills overview to mention the help operation.
4. Add tests that load the packaged catalog and check all current skill assets.

Rollback is straightforward: remove the help sections and docs mentions. No runtime data, APIs, or installed-home migration is involved.

## Open Questions

- Should future generated loop-local skills also inherit this help convention? This change covers packaged Houmao system skills only.
