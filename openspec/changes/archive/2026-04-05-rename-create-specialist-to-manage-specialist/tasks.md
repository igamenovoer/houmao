## 1. Rename and restructure the packaged specialist-management skill

- [x] 1.1 Rename the packaged skill asset from `src/houmao/agents/assets/system_skills/houmao-create-specialist/` to `src/houmao/agents/assets/system_skills/houmao-manage-specialist/` and update packaged metadata such as `agents/openai.yaml`.
- [x] 1.2 Rewrite the top-level `SKILL.md` as an index/router for `project easy specialist create|list|get|remove`, with `project easy instance launch` explicitly out of scope.
- [x] 1.3 Add action-specific local documents for `create`, `list`, `get`, and `remove`, and keep tool-specific credential lookup references attached only to the create action.

## 2. Migrate catalog, installer, and system-skills surfaces

- [x] 2.1 Update the packaged system-skill catalog, set membership, and related helpers so `project-easy` resolves `houmao-manage-specialist` instead of `houmao-create-specialist`.
- [x] 2.2 Implement owned install-state migration so reinstall or auto-install removes previously owned `houmao-create-specialist` paths and records only `houmao-manage-specialist`.
- [x] 2.3 Update `houmao-mgr system-skills` outputs and related tests so list/install/status report the renamed specialist-management skill.

## 3. Update docs and packaged references

- [x] 3.1 Update `docs/reference/cli/system-skills.md` to describe `houmao-manage-specialist` as the packaged project-easy skill and document its create/list/get/remove scope.
- [x] 3.2 Update any packaged skill references and operator docs that still name `houmao-create-specialist` as the active packaged skill so they point to `houmao-manage-specialist`.

## 4. Verify the renamed specialist-management workflow

- [x] 4.1 Update or add focused tests for packaged skill installation, migration from previously owned `houmao-create-specialist` paths, and managed-home projection.
- [x] 4.2 Run focused validation for the system-skill catalog, installer, packaged skill content, and relevant CLI/system-skill tests.
