## Context

`houmao-mgr internals config-drafts generate --intent` accepts an intent JSON object as inline text, `-` for stdin, or a path to a JSON file. The current loader parses JSON successfully, but `generate_config_draft()` only reads the nested `fields` mapping. When a caller supplies valid flat JSON such as `{"name":"general-kimi","tool":"claude","credential":"kimi-coding"}`, the command reports the required fields as missing. That message is technically true after normalization, but it does not tell the caller that the expected shape is `{"fields":{...}}`.

The command tree also has internal graph helpers that read JSON documents from files or stdin. Those are adjacent JSON input surfaces, but they do not currently accept inline JSON text through a general `TEXT` option. This change should inventory maintained JSON input surfaces first, then apply the shared fix-guide contract where a `houmao-mgr` subcommand parses caller-supplied JSON and can provide a useful schema and example.

## Goals / Non-Goals

**Goals:**
- Make failed JSON-input calls self-repairing by naming the failing option, explaining the parse or shape problem, and showing a compact JSON Schema-style expected shape plus a valid example.
- Cover `houmao-mgr internals config-drafts generate --intent` with draft-specific guidance for `project.specialist`, `project.profile`, and `internals.native-agent.launch-dossier`.
- Keep successful command output unchanged.
- Keep fix guides secret-free and safe for terminal output.
- Add tests that prove valid-but-wrong-shape JSON does not look like a shell quoting problem.

**Non-Goals:**
- Do not replace the existing config-draft intent contract with flat JSON in this change.
- Do not introduce a runtime dependency on a JSON Schema validator only to format user guidance.
- Do not redesign Click error rendering or change normal traceback suppression.
- Do not document or validate every downstream domain model with exhaustive JSON Schema.

## Decisions

### Preserve command contracts and improve fix guidance

The implementation should keep `{"fields":{...}}` as the accepted `config-drafts generate --intent` shape. A flat object with known draft fields should fail with a shape diagnostic that explains the wrapper requirement instead of being accepted implicitly.

Alternative considered: accept flat JSON as shorthand. That would reduce friction, but it weakens the existing spec contract and creates two equivalent input forms before the project has a shared policy for JSON text options. This change is about failed-call repair, so it should first make the contract obvious.

### Format fix guides from command-owned metadata

Each JSON input surface should provide a small descriptor containing:
- command path or operation name,
- option name such as `--intent`,
- input source description,
- expected JSON Schema-style object,
- one valid example payload,
- one valid command example when useful.

For config drafts, build the schema and example from the selected `ConfigDraft` metadata. The schema should show an object with a required `fields` object, then required field names and allowed values such as `tool: claude|codex|gemini` when choices exist. The example should be selected per draft id, not copied from ad hoc Markdown prose.

Alternative considered: hand-write one long static error string in `config_drafts/rendering.py`. That would fix the immediate failure, but it would repeat the same mistake if more JSON input surfaces are added later.

### Keep the schema JSON Schema-style but lightweight

The fix guide should render a valid JSON object shaped like JSON Schema, with keys such as `type`, `required`, `properties`, `additionalProperties`, and `enum` where useful. It does not need to be validated by `jsonschema` at runtime. Existing Python validators can continue to own parsing and field checks.

Alternative considered: add `jsonschema` as a dependency and validate input through generated schemas. That is heavier than the problem requires and risks coupling command validation to diagnostic display details.

### Report multiple blocker classes without hiding the schema

Invalid JSON, non-object JSON, missing `fields`, non-object `fields`, unsupported fields, invalid field values, and missing required fields should all include the same fix-guide section after the primary error. The first line should stay concise, and the schema/example should give the caller an immediate correction target.

For config drafts, when a flat object contains keys that match the selected draft's declared fields, the primary message should explicitly say that the intent fields must be nested under `fields`. If the object contains unrelated top-level keys, the primary message should still mention the missing `fields` mapping and then show the schema.

### Keep sensitive values out of examples

Examples must use placeholder-like safe values such as `reviewer`, `reviewer-creds`, and `general-kimi`. Fix guides must not echo arbitrary credential material, prompt text, mailbox bodies, auth tokens, bearer tokens, or environment secret values. When an error needs to name fields, it should name keys rather than values unless the value is a safe enum such as a tool name.

## Risks / Trade-offs

- [Risk] Error output becomes too long for simple parse failures. -> Mitigation: keep the first line concise and make the schema/example compact.
- [Risk] A schema-like guide drifts from the actual validator. -> Mitigation: generate config-draft guides from `ConfigDraft` field metadata and test all registered draft ids.
- [Risk] Callers expect machine-readable JSON errors under `--print-json`. -> Mitigation: keep this change scoped to fix-guide content unless existing output style helpers already support structured errors; add a future task if machine-readable error payloads become necessary.
- [Risk] The inventory finds JSON file-only internals whose ideal examples are graph-specific and larger than a terminal error should show. -> Mitigation: classify those surfaces during implementation and document any deferred surfaces with rationale.

## Migration Plan

No data migration is required. Rollout is limited to CLI diagnostics, packaged skill guidance, and documentation. Rollback is a code revert because successful payload formats and storage state remain unchanged.

## Open Questions

- Should a later change accept flat `config-drafts --intent` JSON as a shorthand after the clearer diagnostics land?
- Should `houmao-mgr --print-json` eventually emit structured error payloads for machine callers, separate from Click's plain error rendering?
