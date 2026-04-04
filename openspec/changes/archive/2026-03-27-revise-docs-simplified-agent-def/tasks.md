## 1. Delete Obsolete Reference Docs

- [x] 1.1 Delete `docs/reference/agents_brains.md` (legacy recipe/blueprint/brains walkthrough).
- [x] 1.2 Delete `docs/reference/build-phase/brain-builder.md` (old build pipeline walkthrough with obsolete paths and Mermaid diagram).
- [x] 1.3 Delete `docs/reference/build-phase/recipes-and-adapters.md` (old BrainRecipe/ToolAdapter composition model).

## 2. Fix Navigation And Cross-References

- [x] 2.1 Update `mkdocs.yml` to remove nav entries for the three deleted files (`agents_brains.md`, `brain-builder.md`, `recipes-and-adapters.md`).
- [x] 2.2 Search all surviving `docs/**/*.md` and `docs/index.md` for links to the three deleted files and remove or redirect them to the getting-started equivalents (`getting-started/overview.md`, `getting-started/agent-definitions.md`).

## 3. Rewrite README Agent-Definition Section

- [x] 3.1 Rewrite the README agent-definition directory section (approx lines 186–370) to document the new `tools/`/`roles/`/`skills/`/presets layout with inline examples. Include: directory tree, tool adapter overview, setup bundles, auth bundles, preset files, skills, and role packages. Derive examples from `tests/fixtures/agents/`.
- [x] 3.2 Fix scattered old-term references in the README upper sections: replace "brains + roles + optional blueprints" with current terminology at lines ~27, ~33, ~55 and any other occurrences.

## 4. Update LLM Context Files

- [x] 4.1 Update `AGENTS.md`: replace `brains/api-creds/` fixture paths with `tools/<tool>/auth/` paths. Update the agent definition directory description and committed-inputs list to match the new layout.
- [x] 4.2 Update `CLAUDE.md`: fix old layout tree (`brains/tool-adapters/`, `brains/cli-configs/`, `brains/api-creds/`, `brains/brain-recipes/`), replace `config_profile`/`credential_profile` terms with `setup`/`auth`, update the Agent Definition Directory section and Source Layout references.
- [x] 4.3 Update `GEMINI.md`: fix old layout tree and Key Concepts section. Replace `config_profile`/`credential_profile` with `setup`/`auth`. Update the Agent Definition Directory and Architecture sections.
- [x] 4.4 Update `.github/copilot-instructions.md`: fix the "Committed inputs" block (`brains/tool-adapters/`, `brains/skills/`, `brains/cli-configs/`, `brains/brain-recipes/`) to use new paths. Update convention descriptions referencing `config profiles`, `credential profiles`, `recipes`, and `blueprints`.

## 5. Fix Surviving Reference Docs

- [x] 5.1 Update `docs/reference/houmao_server_agent_api_live_suite.md`: replace 5 old-path references (`brains/brain-recipes/`, `brains/api-creds/`, `brains/cli-configs/`) with current layout paths. Verify against actual demo pack directory structure after the `fix-demo-agent-launching` change.
- [x] 5.2 Check `docs/reference/build-phase/launch-overrides.md` for any remaining old terminology (`recipe`, `config_profile`) and update to current terms (`preset`, `setup`) if found.

## 6. Verify

- [x] 6.1 Run a global grep across `README.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `docs/**/*.md`, and `mkdocs.yml` for: `brains/brain-recipes`, `brains/cli-configs`, `brains/api-creds`, `brains/tool-adapters`, `config_profile`, `credential_profile`, `blueprints/`. Confirm zero matches in documentation and context files.
- [x] 6.2 Run `pixi run docs-build` and confirm the MkDocs site builds cleanly with no warnings about missing files or broken nav entries.
