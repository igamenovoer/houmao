## 1. Fix user-facing docs

- [x] 1.1 In `docs/reference/system-files/agents-and-runtime.md` line 71, update `schema_version=2` to `schema_version=4`
- [x] 1.2 In the same file line 78, update the operational note from "rejects legacy `schema_version=1`" to "rejects any `schema_version` other than 4"

## 2. Fix spec example

- [x] 2.1 In `openspec/specs/brain-launch-runtime/spec.md` line 806, update the example from `session_manifest.v3.schema.json` to `session_manifest.v4.schema.json`

## 3. Validate

- [x] 3.1 Verify no other docs or specs reference deleted schema filenames (`session_manifest.v2` or `session_manifest.v3`) with `grep -r`
- [x] 3.2 Run `openspec validate brain-launch-runtime --type spec --strict --json` to confirm the updated spec is valid
