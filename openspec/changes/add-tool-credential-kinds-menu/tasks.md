## 1. Create credential kinds references for `houmao-specialist-mgr`

- [ ] 1.1 Create `src/houmao/agents/assets/system_skills/houmao-specialist-mgr/references/claude-credential-kinds.md` enumerating API key (`--api-key`), auth token (`--claude-auth-token`), OAuth token (`--claude-oauth-token`), and vendor-login config-dir (`--claude-config-dir`) kinds, with optional modifiers `--base-url`, `--claude-model`, and `--claude-state-template-file`; include a Discovery Shortcuts section citing `claude-credential-lookup.md`
- [ ] 1.2 Create `src/houmao/agents/assets/system_skills/houmao-specialist-mgr/references/codex-credential-kinds.md` enumerating API key (`--api-key`) and cached login state (`--codex-auth-json`) kinds, with optional modifiers `--base-url` and `--codex-org-id`; include a Discovery Shortcuts section citing `codex-credential-lookup.md`
- [ ] 1.3 Create `src/houmao/agents/assets/system_skills/houmao-specialist-mgr/references/gemini-credential-kinds.md` enumerating API key (`--api-key`), Vertex AI (`--google-api-key` + `--use-vertex-ai`), and OAuth creds (`--gemini-oauth-creds`) kinds, with optional modifier `--base-url`; include a Discovery Shortcuts section citing `gemini-credential-lookup.md`

## 2. Create credential kinds references for `houmao-credential-mgr`

- [ ] 2.1 Create `src/houmao/agents/assets/system_skills/houmao-credential-mgr/references/claude-credential-kinds.md` enumerating API key (`--api-key`), auth token (`--auth-token`), OAuth token (`--oauth-token`), and vendor-login config-dir (`--config-dir`) kinds; note that discovery modes are not supported by `project credentials claude add` and point to `houmao-specialist-mgr` for discovery
- [ ] 2.2 Create `src/houmao/agents/assets/system_skills/houmao-credential-mgr/references/codex-credential-kinds.md` enumerating API key (`--api-key`) and cached login state (`--auth-json`) kinds; note the discovery gap and point to `houmao-specialist-mgr`
- [ ] 2.3 Create `src/houmao/agents/assets/system_skills/houmao-credential-mgr/references/gemini-credential-kinds.md` enumerating API key (`--api-key`), Vertex AI (`--google-api-key` + `--use-vertex-ai`), and OAuth creds (`--oauth-creds`) kinds; note the discovery gap and point to `houmao-specialist-mgr`

## 3. Update action pages to cite kinds references

- [ ] 3.1 Update `houmao-specialist-mgr/actions/create.md` step 9 (ask-for-missing-auth) to cite the per-tool kinds reference when presenting auth-input options to the user
- [ ] 3.2 Update `houmao-credential-mgr/actions/add.md` step 3 (ask-the-user) to cite the per-tool kinds reference when presenting auth-input options to the user

## 4. Update SKILL.md files

- [ ] 4.1 Update `houmao-specialist-mgr/SKILL.md` References section to list the three new `*-credential-kinds.md` references
- [ ] 4.2 Update `houmao-credential-mgr/SKILL.md` to list the three new `*-credential-kinds.md` references as the credential kinds menu surface

## 5. Update delta specs

- [ ] 5.1 Update `openspec/specs/houmao-create-specialist-skill/spec.md` with the additive requirement for per-tool credential kinds references in `houmao-specialist-mgr`
- [ ] 5.2 Update `openspec/specs/houmao-manage-credentials-skill/spec.md` with the additive requirement for per-tool credential kinds references in `houmao-credential-mgr`

## 6. Validate

- [ ] 6.1 Run `pixi run lint` and fix any issues in new or updated files
- [ ] 6.2 Run `pixi run pytest tests/unit/agents/test_system_skills.py tests/unit/agents/test_brain_builder.py::test_build_brain_home_projects_selected_components_and_manifest` and update test assertions if they fail due to the new reference files or changed action-page text
