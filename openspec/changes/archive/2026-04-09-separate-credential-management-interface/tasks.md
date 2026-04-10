## 1. Command Tree And Target Resolution

- [x] 1.1 Add `houmao-mgr credentials` and `houmao-mgr project credentials` to the maintained Click command tree and help surfaces.
- [x] 1.2 Implement shared credential-target resolution for explicit `--agent-def-dir`, explicit project selection, `HOUMAO_AGENT_DEF_DIR`, active project-overlay discovery, and overlay-managed compatibility-tree detection.
- [x] 1.3 Update command wording and structured output so credential commands are presented as the supported concern-oriented surface instead of `project agents tools <tool> auth ...`.

## 2. Shared Credential Backend

- [x] 2.1 Extract the adapter-driven credential validation and temporary-tree mutation logic from the current project auth helpers into backend-neutral helpers.
- [x] 2.2 Wire the project-backed credential actions to the extracted helpers while preserving catalog-backed display-name and bundle-ref behavior.
- [x] 2.3 Implement the plain agent-definition-dir backend for `list|get|add|set|remove` over `tools/<tool>/auth/<name>/`.
- [x] 2.4 Implement plain agent-definition-dir `rename` with maintained preset and launch-profile auth-reference rewrites plus rewritten-file reporting.

## 3. Remove Old Ownership And Update Routing

- [x] 3.1 Remove maintained credential CRUD from `project agents tools <tool>` while preserving tool inspection and setup-bundle behavior.
- [x] 3.2 Update the packaged `houmao-credential-mgr` skill assets and related routing guidance to use `credentials ...` / `project credentials ...`.
- [x] 3.3 Update CLI and getting-started docs to document the new credential command families and the removal of `project agents tools <tool> auth ...` as the canonical route.

## 4. Verification

- [x] 4.1 Add or update tests for the new top-level/project command-family help surfaces and credential target-resolution rules.
- [x] 4.2 Add or update tests for project-backed credential CRUD, safe inspection, and metadata-only rename behavior.
- [x] 4.3 Add or update tests for plain agent-definition-dir credential CRUD and rename-driven YAML reference rewrites.
