## 1. Inventory And Scope

- [x] 1.1 Inventory maintained `houmao-mgr` JSON input surfaces that parse inline JSON text, stdin JSON, or JSON files, including `internals config-drafts generate --intent` and graph internals JSON readers.
- [x] 1.2 Create change-local scan notes that classify covered surfaces and any deferred file-only, test-only, demo-only, non-public, or larger-design surfaces.
- [x] 1.3 Confirm the initial implementation scope covers `internals config-drafts generate --intent` for all registered draft ids.

## 2. Shared Fix-Guide Support

- [x] 2.1 Add a small JSON input fix-guide formatter under the `houmao.srv_ctrl` command/config-draft layer without adding a runtime JSON Schema validation dependency.
- [x] 2.2 Ensure the formatter renders a concise primary problem, input option or source, JSON Schema-style expected shape, and safe example payload or command.
- [x] 2.3 Ensure the formatter avoids echoing submitted secret material and uses safe placeholder values in examples.

## 3. Config Draft Diagnostics

- [x] 3.1 Generate draft-specific intent schemas and examples from `ConfigDraft` metadata, including required fields and enum choices.
- [x] 3.2 Update `load_draft_intent()` and config-draft generation error paths so invalid JSON, non-object JSON, missing `fields`, non-object `fields`, unsupported fields, invalid field values, and missing required fields include the fix guide.
- [x] 3.3 Add a dedicated diagnostic for flat objects that contain selected draft field names, explaining that those fields must be nested under `fields`.
- [x] 3.4 Preserve existing successful YAML and JSON output for valid config-draft generation.

## 4. Agent-Facing Guidance

- [x] 4.1 Update packaged `houmao-agent-definition` guidance to show `{"fields":{...}}` for specialist, profile, launch-dossier, and create-agent-fast-forward config-draft examples.
- [x] 4.2 Update relevant CLI reference documentation so `config-drafts generate --intent` examples match the required `fields` envelope and failure fix guide examples.
- [x] 4.3 Update packaged skill contract tests that currently assert ambiguous bare `--intent '<json>'` or "intent fields" wording.

## 5. Tests And Verification

- [x] 5.1 Add unit tests for flat `project.specialist` intent showing the `fields` wrapper diagnostic, schema, and valid example.
- [x] 5.2 Add unit tests for missing required fields, invalid enum values, non-object `fields`, non-object top-level JSON, and invalid JSON showing schema and example guidance.
- [x] 5.3 Add tests proving valid config-draft generation output remains unchanged for all registered draft ids.
- [x] 5.4 Add or update tests proving secret-looking submitted values are not echoed in fix-guide examples.
- [x] 5.5 Run focused config-draft and system-skill tests, then run `pixi run test` if the implementation touches shared command helpers.
