## 1. Installer And CLI

- [x] 1.1 Add Copilot to the shared system-skill projection destination map with `skills` as the home-relative destination.
- [x] 1.2 Add Copilot to `houmao-mgr system-skills install|status` home resolution using `COPILOT_HOME` and `<cwd>/.github` as the project-scoped default.
- [x] 1.3 Preserve existing copy, symlink, selected-set, explicit-skill, CLI-default, and status behavior for Copilot.

## 2. Tests

- [x] 2.1 Add unit coverage for shared Copilot projection and status discovery, including copy and symlink projection.
- [x] 2.2 Add CLI coverage for omitted-home Copilot default installs to `.github/skills`, `COPILOT_HOME` redirection, explicit `--home ~/.copilot`-style installs, and status home resolution.

## 3. Documentation

- [x] 3.1 Update the `system-skills` CLI reference to list Copilot support, `COPILOT_HOME`, `<cwd>/.github`, and Copilot projection examples.
- [x] 3.2 Update the system-skills overview guide to mention Copilot explicit installs and the local-runtime caveat.

## 4. Verification

- [x] 4.1 Run focused system-skill unit tests.
- [x] 4.2 Run OpenSpec validation for `add-copilot-system-skills`.
