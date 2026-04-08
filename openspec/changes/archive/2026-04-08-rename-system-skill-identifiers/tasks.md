## 1. Rename the packaged skill assets

- [x] 1.1 Rename the four packaged system-skill directories to `houmao-agent-definition`, `houmao-agent-instance`, `houmao-credential-mgr`, and `houmao-specialist-mgr`, and update their `agents/openai.yaml` metadata.
- [x] 1.2 Update the renamed skill trees so `SKILL.md`, action pages, and reference pages use the new self-identifiers and the renamed cross-skill routing targets consistently.

## 2. Cut over catalog and installer behavior

- [x] 2.1 Update the packaged system-skill catalog, related constants, and any current-skill inventory helpers so the new names are the only active public packaged identifiers.
- [x] 2.2 Extend the shared install-state rename migration so reinstall or auto-install removes previously owned paths for `houmao-manage-specialist`, `houmao-manage-credentials`, `houmao-manage-agent-definition`, and `houmao-manage-agent-instance` and records only the renamed current skills.
- [x] 2.3 Update `houmao-mgr system-skills` list/install/status behavior and focused tests so reported skill names, projected directories, and CLI-default selections all use the renamed identifiers.

## 3. Refresh current docs and spec-aligned text

- [x] 3.1 Update `README.md`, `docs/getting-started/system-skills-overview.md`, and `docs/reference/cli/system-skills.md` so the packaged inventory and cross-skill boundary text use the renamed skills consistently.
- [x] 3.2 Update current in-repo requirement-aligned text and focused assertions outside the main docs, including packaged skill references and tests that still treat the superseded names as current.

## 4. Verify the rename and migration paths

- [x] 4.1 Add or update focused tests for catalog loading, explicit install, status reporting, and owned-path migration from each superseded skill name to its renamed replacement.
- [x] 4.2 Run the relevant OpenSpec validation and targeted system-skill test coverage to confirm the renamed inventory, unchanged set topology, and install-state migration behavior.
