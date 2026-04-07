## 1. Revise the system-skills CLI contract

- [x] 1.1 Update `houmao-mgr system-skills install` so `--home` becomes optional and omitted selection resolves the packaged CLI-default set list.
- [x] 1.2 Add effective-home resolution for `install` and `status` with precedence `--home` > tool-native home env var > project-scoped default, including the Gemini `<cwd>` home-root rule.
- [x] 1.3 Remove the public `--default` flag from `system-skills install` help, parsing, and operator-facing error/summary text while preserving repeatable `--set` and `--skill`.

## 2. Cover the new behavior with focused tests

- [x] 2.1 Update `tests/unit/srv_ctrl/test_system_skills_commands.py` to cover explicit-home precedence, env-backed home redirection, and project-scoped default homes for Claude, Codex, and Gemini.
- [x] 2.2 Add focused assertions that omitted `--set` and `--skill` install the CLI-default set list and that Gemini default installs land under `<cwd>/.agents/skills/`.
- [x] 2.3 Add regression coverage that `system-skills install --default` is rejected and that `status` reports the effective resolved home when `--home` is omitted.

## 3. Update reference docs and examples

- [x] 3.1 Revise `docs/reference/cli/system-skills.md` to show the new command shape, effective-home precedence, Gemini's project-root default, and omitted-selection default behavior.
- [x] 3.2 Revise `docs/reference/cli/houmao-mgr.md` and any related CLI summaries so `system-skills` no longer documents `--default` or explicit-home-only behavior.
- [x] 3.3 Update remaining user-facing examples such as `README.md` and `docs/reference/mailbox/quickstart.md` to replace `--default` examples with the new default-selection contract and rerun the relevant focused test/docs checks.
