## 1. Policy Model And Installer Support

- [x] 1.1 Add a managed system-skill selection policy model, parser, serializer, and validator against the packaged system-skill catalog.
- [x] 1.2 Implement source-policy and profile-policy resolution for default, inherit, extend, replace, and none modes.
- [x] 1.3 Add a managed-home system-skill sync helper that removes unselected current Houmao-owned system-skill paths and retired paths while preserving unrelated user skills.
- [x] 1.4 Add unit tests for policy parsing, selector validation, resolution ordering, deduplication, invalid mode/selector errors, and sync cleanup behavior.

## 2. Recipe And Specialist Source Policy

- [x] 2.1 Extend recipe launch parsing to accept `launch.system_skills` and expose it on parsed presets.
- [x] 2.2 Extend specialist create/set request handling to build and persist specialist-owned system-skill policy in the generated recipe launch payload.
- [x] 2.3 Extend specialist inspection output to report stored system-skill policy separately from project skill selections.
- [x] 2.4 Add tests for specialist create, set, clear, invalid selectors, and generated compatibility recipe YAML.

## 3. Launch-Profile Storage And Projection

- [x] 3.1 Bump the project catalog schema and add launch-profile storage for system-skill policy with omitted/inherit defaults.
- [x] 3.2 Extend launch-profile catalog entries, load/store paths, compatibility YAML rendering, and structured inspection payloads.
- [x] 3.3 Preserve system-skill policy on patch mutations and clear it on replacement mutations unless replacement supplies a new policy.
- [x] 3.4 Add catalog and projection tests for easy profiles and explicit launch profiles.

## 4. CLI Surfaces

- [x] 4.1 Add `--system-skill-set`, `--system-skill`, `--system-skills-mode`, `--no-system-skills`, and `--clear-system-skills` handling to `project easy specialist create/set`.
- [x] 4.2 Add the same stored-policy option family to `project easy profile create/set`.
- [x] 4.3 Add the same stored-policy option family to `project agents launch-profiles add/set`.
- [x] 4.4 Add mutual-exclusion and mode-specific validation errors for disabled mode, clear mode, selectors, and empty replacement selections.
- [x] 4.5 Add CLI tests for plain and JSON output on create/get/set flows.

## 5. Build And Launch Runtime Integration

- [x] 5.1 Extend `BuildRequest` and launch resolution to carry source recipe and launch-profile system-skill policies into brain construction.
- [x] 5.2 Merge source and profile policies during managed launch, including profile inherit, extend, replace, and none semantics.
- [x] 5.3 Reject selected project registered skills and profile-private skills whose names collide with current packaged Houmao system-skill names.
- [x] 5.4 Replace the fixed managed-launch auto-install call with resolved managed-home system-skill sync.
- [x] 5.5 Record requested and resolved system-skill provenance in the build manifest or runtime launch metadata.
- [x] 5.6 Add runtime/build tests for source additive policy, profile replacement policy, disabled policy on reused homes, collision rejection, Gemini projection roots, and manifest provenance.

## 6. Documentation

- [x] 6.1 Update the system-skills overview and CLI reference to distinguish explicit tool-home installation from managed launch system-skill policy.
- [x] 6.2 Update easy specialist docs with examples for adding `houmao-utils-llm-wiki`, disabling system skills, and clearing policy.
- [x] 6.3 Update launch-profile docs with inherit, extend, replace, and none semantics.
- [x] 6.4 Update agent-definition/build/runtime references for `launch.system_skills` and managed-home reuse cleanup behavior.

## 7. Verification

- [x] 7.1 Run focused unit tests for system skills, definition parsing, project catalog, project easy CLI, launch-profile CLI, and brain builder.
- [x] 7.2 Run `pixi run test` after focused suites pass.
- [x] 7.3 Run `pixi run lint` and `pixi run typecheck`.
- [x] 7.4 Run `pixi run openspec validate configure-managed-system-skills --strict` or the repository's equivalent OpenSpec validation command.
