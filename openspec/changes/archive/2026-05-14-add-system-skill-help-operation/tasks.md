## 1. Skill Help Contract

- [x] 1.1 Add a standard `## Help` section to every current top-level packaged system skill declared in `catalog.toml`.
- [x] 1.2 Ensure each help section states read-only behavior and says not to run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help.
- [x] 1.3 Ensure each help section summarizes the skill purpose and available functionality as a short list or table.
- [x] 1.4 Ensure each help section includes common starting prompts or examples users can copy or adapt.
- [x] 1.5 Ensure each help section names related skills, out-of-scope concerns, or routing boundaries where adjacent work belongs elsewhere.

## 2. Routing Integration

- [x] 2.1 Update operation-heavy skills so `help` is listed as a meta operation beside existing operations and is handled before default operations.
- [x] 2.2 Update router-style skills so explicit help intent is handled before action page, branch page, transport page, pattern, reference, or subskill selection.
- [x] 2.3 Keep help trigger wording narrow so "help me do X" still routes to the actual workflow when the user clearly asks for supported work.
- [x] 2.4 Leave retired legacy skill assets under `src/houmao/agents/assets/system_skills/legacy/` unchanged.

## 3. Documentation

- [x] 3.1 Update the README system-skill guidance to mention explicit skill help and include at least one example help prompt.
- [x] 3.2 Update `docs/getting-started/system-skills-overview.md` to explain the standard help convention, read-only behavior, and explicit-help versus workflow-request boundary.

## 4. Tests And Verification

- [x] 4.1 Add or update system-skill content tests to verify every current catalog skill has a top-level help section.
- [x] 4.2 Add or update tests to verify help sections include read-only behavior, available functionality, common prompts, and related-skill or boundary guidance.
- [x] 4.3 Add or update docs guard tests for README and system-skills overview help guidance.
- [x] 4.4 Run focused system-skill and docs tests.
- [x] 4.5 Run `pixi run lint` if Python tests change.
- [x] 4.6 Run `openspec validate add-system-skill-help-operation --strict`.
