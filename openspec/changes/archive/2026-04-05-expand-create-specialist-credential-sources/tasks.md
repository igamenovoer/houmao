## 1. Skill Contract

- [x] 1.1 Rewrite `src/houmao/agents/assets/system_skills/houmao-create-specialist/SKILL.md` around four credential-source modes: explicit auth, user-directed env lookup, user-directed directory scan, and tool-specific auto discovery.
- [x] 1.2 Preserve the existing launcher-resolution and credential-bundle reuse behavior while updating the no-scan guardrails so they only permit scanning when one of the supported credential-source modes is explicitly active.

## 2. Tool-Specific Lookup References

- [x] 2.1 Add a Claude credential lookup reference page that documents deployment-realistic Claude auth surfaces using official docs, `extern/orphan/claude-code`, and installed `claude` CLI behavior.
- [x] 2.2 Add a Codex credential lookup reference page that documents deployment-realistic Codex auth surfaces using official docs, `extern/orphan/codex`, and installed `codex` CLI behavior.
- [x] 2.3 Add a Gemini credential lookup reference page that documents deployment-realistic Gemini auth surfaces using official docs, `extern/orphan/gemini-cli`, and installed `gemini` CLI behavior.
- [x] 2.4 Ensure all tool-specific reference pages avoid `tests/fixtures/agents`, demo fixtures, and other repository-only lookup paths.

## 3. Validation

- [x] 3.1 Update `tests/unit/agents/test_system_skills.py` to assert the packaged skill content and reference pages describe the new credential-source modes and avoid fixture-only deployment guidance.
- [x] 3.2 Run focused validation for the updated system skill content and any related docs or lint checks needed by the touched files.
