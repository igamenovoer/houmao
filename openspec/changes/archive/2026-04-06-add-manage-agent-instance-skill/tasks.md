## 1. Skill Asset

- [x] 1.1 Create the packaged `src/houmao/agents/assets/system_skills/houmao-manage-agent-instance/` skill tree with `SKILL.md`, action docs, and `agents/openai.yaml`
- [x] 1.2 Implement the top-level router guidance for `launch`, `join`, `list`, `stop`, and `cleanup` with the approved lifecycle-only scope
- [x] 1.3 Write the action guidance so direct launch uses `agents launch`, specialist-backed launch uses `project easy instance launch`, join uses `agents join`, and cleanup stays on `agents cleanup session|logs`

## 2. Catalog And Installer

- [x] 2.1 Add `houmao-manage-agent-instance` to the packaged system-skill catalog with its own flat asset entry
- [x] 2.2 Add a dedicated named catalog set for the new lifecycle skill and update `cli_default_sets` to include that set alongside `project-easy`
- [x] 2.3 Update system-skill loader and installer coverage so catalog inventory, resolved default installs, and recorded installed skills reflect the new packaged skill

## 3. Docs

- [x] 3.1 Update `docs/reference/cli/system-skills.md` to document `houmao-manage-agent-instance`, its lifecycle-only boundary, and its relationship to `houmao-manage-specialist`
- [x] 3.2 Update CLI reference docs where needed so the expanded CLI-default system-skill selection is described accurately

## 4. Verification

- [x] 4.1 Add or update unit tests for the system-skill catalog, installer resolution, and `houmao-mgr system-skills` CLI payloads
- [x] 4.2 Validate the new skill content with the repo skill validator and run the focused Ruff/pytest coverage for changed system-skill and CLI code
