## 1. Config-Draft Core

- [x] 1.1 Create a focused config-draft package under `src/houmao/srv_ctrl/` with typed draft result, blocker, and registry models.
- [x] 1.2 Implement intent loading for inline JSON, stdin, and JSON file paths using the same safe input conventions as command-template rendering.
- [x] 1.3 Implement deterministic YAML serialization for generated draft payloads without command-template schema keys.
- [x] 1.4 Add registry validation for duplicate draft ids and unknown draft id diagnostics.

## 2. CLI Surface

- [x] 2.1 Add `houmao-mgr internals config-drafts list` with compact JSON/plain output.
- [x] 2.2 Add `houmao-mgr internals config-drafts generate --id <draft-id> --intent <json-or-path>` for raw YAML generation.
- [x] 2.3 Define and test blocker behavior for missing, unsupported, invalid, and conflicting draft inputs.
- [x] 2.4 Decide and codify how `--print-json` interacts with successful YAML generation and blocker output.

## 3. Draft Generators

- [x] 3.1 Implement `project.easy.specialist` draft generation with high-level specialist semantics and fixed config kind.
- [x] 3.2 Implement `project.easy.profile` draft generation with fixed `profile_lane: easy_profile` and specialist source kind.
- [x] 3.3 Implement `project.agents.launch-profile` draft generation with fixed recipe-backed source kind.
- [x] 3.4 Reuse or extract shared payload builders from project catalog projection code where draft and projection shapes should match.
- [x] 3.5 Verify generated drafts omit absent optional fields, clear flags, command-template field metadata, omitted-field prose, and target argv.

## 4. Skill Guidance Migration

- [x] 4.1 Update `houmao-agent-definition` top-level and lane subskills to use `internals config-drafts generate` for specialists, profiles, raw-profiles, and profile preparation in fast-forward flows.
- [x] 4.2 Keep `houmao-agent-definition` role, recipe, and launch-command guidance on command-template rendering where those workflows remain command-oriented.
- [x] 4.3 Update `houmao-memory-mgr` profile memo-seed guidance to route profile-document authoring through config drafts.
- [x] 4.4 Update skill text regression tests so config-authoring guidance no longer requires `command-templates show` for migrated flows.

## 5. Tests And Verification

- [x] 5.1 Add unit tests for config-draft registry inventory, duplicate-id detection, and unknown-id errors.
- [x] 5.2 Add unit tests for each initial draft generator's YAML payload shape and fixed lane/source values.
- [x] 5.3 Add CLI tests for `internals config-drafts list` and `generate`, including blocker cases.
- [x] 5.4 Add regression tests that existing command-template rendering remains available for command-oriented workflows.
- [x] 5.5 Run `pixi run test` for the focused and broader unit suites touched by the change.
- [x] 5.6 Run `pixi run lint` and `pixi run typecheck`.
