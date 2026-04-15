## Why

When `houmao-specialist-mgr` or `houmao-credential-mgr` asks a user for a credential during specialist creation or `project credentials <tool> add`, the skill tells the agent to "ask for supported auth inputs" but does not enumerate the user-facing credential kinds available for the selected tool. Today's per-tool lookup references (`claude-credential-lookup.md`, `codex-credential-lookup.md`, `gemini-credential-lookup.md`) cover discovery and importability, and the action pages list `--flag` surfaces, but neither place presents a clean "pick one of these kinds" menu to the user.

This matters because each tool has more than one credential kind (Claude alone ships API key, auth token, OAuth token, and a vendor-login config-dir lane; Codex ships API key and `auth.json`; Gemini ships API key, Vertex AI key, and OAuth creds file). First-time users don't know what kinds exist or which one matches their situation, so the agent either guesses or asks a terse command-flag-style question.

This change adds per-tool "credential kinds" reference pages to both `houmao-specialist-mgr` and `houmao-credential-mgr` (Option B from the exploration discussion: accept small duplication between the two skills because each is an independently installed asset directory and cross-skill links do not resolve after `pip install`). Each kinds page enumerates the selectable kinds for that tool, describes what the user would provide for each, maps each kind to the corresponding CLI flag for that skill's command surface, and cites the existing lookup reference for discovery-mode shortcuts. The one-shot `project easy specialist create --<tool-auth-flag> ...` path in `houmao-specialist-mgr` stays exactly as it is today; this change is purely about presenting better choices when the agent needs to ask the user.

## What Changes

- Add three new reference pages under `src/houmao/agents/assets/system_skills/houmao-specialist-mgr/references/`: `claude-credential-kinds.md`, `codex-credential-kinds.md`, `gemini-credential-kinds.md`. Each page enumerates selectable credential kinds for its tool, names what the user provides for each kind, and maps each kind to the `project easy specialist create` flag it satisfies.
- Add a new `references/` directory under `src/houmao/agents/assets/system_skills/houmao-credential-mgr/` and add three new reference pages there: `claude-credential-kinds.md`, `codex-credential-kinds.md`, `gemini-credential-kinds.md`. Each page enumerates selectable credential kinds for its tool, names what the user provides for each kind, and maps each kind to the `project credentials <tool> add` flag it satisfies.
- Update `houmao-specialist-mgr/actions/create.md` step 9 (the "ask the user for missing auth inputs" step) to cite the kinds reference for the selected tool when the agent has to present auth-input options to the user.
- Update `houmao-credential-mgr/actions/add.md` step 3 (the "ask the user before proceeding" step) to cite the kinds reference for the selected tool when the agent has to present auth-input options to the user.
- Update `houmao-specialist-mgr/SKILL.md` References section to list the three new kinds references.
- Update `houmao-credential-mgr/SKILL.md` to list the three new kinds references as the credential kinds menu surface.
- Accept controlled duplication between the two skills: each skill's per-tool kinds page covers the same kinds (API key, OAuth token, auth token, vendor login files, Vertex AI lane, etc.) but maps those kinds to the flag shape of its own command (`project easy specialist create` vs `project credentials <tool> add`). The duplication is intentional because each skill ships as its own installed asset directory.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `houmao-create-specialist-skill`: add a requirement that `houmao-specialist-mgr` ships per-tool credential kinds references and cites them from the create action when asking the user for missing auth inputs.
- `houmao-manage-credentials-skill`: add a requirement that `houmao-credential-mgr` ships per-tool credential kinds references under a new `references/` directory and cites them from the add action when asking the user for missing auth inputs.

## Impact

- Affected packaged asset directories:
  - `src/houmao/agents/assets/system_skills/houmao-specialist-mgr/` — three new reference files, `SKILL.md` and `actions/create.md` updated.
  - `src/houmao/agents/assets/system_skills/houmao-credential-mgr/` — new `references/` directory with three reference files, `SKILL.md` and `actions/add.md` updated.
- Affected specs: `openspec/specs/houmao-create-specialist-skill/spec.md` and `openspec/specs/houmao-manage-credentials-skill/spec.md` receive additive requirements.
- No CLI command shape changes. No Python source changes. No changes to the one-shot `project easy specialist create --<auth-flag>` path. No changes to the existing lookup references (`*-credential-lookup.md`). No changes to the discovery-mode workflow in `actions/create.md`. No changes to `houmao-touring` (existing routing to the owning skill is sufficient).
- Tests under `tests/unit/agents/test_system_skills.py` may need light updates to assert the presence of the new reference files and the new cite-lines in the action pages, if the test suite asserts those substrings today.
