## 1. Catalog And Packaged Assets

- [x] 1.1 Remove `[skills.houmao-utils-llm-wiki]` from `src/houmao/agents/assets/system_skills/catalog.toml`.
- [x] 1.2 Remove `houmao-utils-llm-wiki` from every catalog named set and auto-install/default resolved selection.
- [x] 1.3 Confirm `houmao-utils-llm-wiki` is not added to `retired_skill_names`.
- [x] 1.4 Delete `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/`.
- [x] 1.5 Remove code constants or helper references dedicated to `houmao-utils-llm-wiki`.

## 2. Runtime And CLI Behavior

- [x] 2.1 Ensure explicit system-skill selection of `houmao-utils-llm-wiki` fails as an unknown system skill before mutating target homes.
- [x] 2.2 Ensure source recipe, specialist, launch-profile, and project-profile policies that name `houmao-utils-llm-wiki` fail clearly during validation or launch preparation.
- [x] 2.3 Ensure `system-skills list`, `install`, `status`, and `uninstall` do not report `houmao-utils-llm-wiki` as current or retired inventory.
- [x] 2.4 Ensure stale `skills/houmao-utils-llm-wiki/` paths are preserved as unrecognized external/user-managed content.
- [x] 2.5 Replace test fixtures and examples that used `houmao-utils-llm-wiki` only as a valid explicit system-skill selector with `houmao-utils-workspace-mgr` or another current skill.

## 3. Documentation And Specs

- [x] 3.1 Update getting-started docs to remove LLM Wiki system-skill rows, install examples, set membership text, and concern-routing guidance.
- [x] 3.2 Update CLI reference docs to remove LLM Wiki system-skill inventory, install examples, status/uninstall expectations, and named-set prose.
- [x] 3.3 Update README system-skills catalog content to omit `houmao-utils-llm-wiki`.
- [x] 3.4 Update project/profile documentation examples that currently use `houmao-utils-llm-wiki` as a managed system-skill selector.
- [x] 3.5 Leave external user-managed skill-home symlinks and other out-of-catalog copies for the user to clean manually.

## 4. Tests And Verification

- [x] 4.1 Update unit tests for catalog loading, resolved install sets, packaged asset shape, install/sync/uninstall behavior, and system-skills CLI output.
- [x] 4.2 Update project, profile, recipe, and brain-builder tests that currently use `houmao-utils-llm-wiki` as a valid packaged system-skill name.
- [x] 4.3 Add or update tests asserting `houmao-utils-llm-wiki` explicit selectors fail as unknown and stale paths are not cleaned as Houmao-owned retired projections.
- [x] 4.4 Run focused system-skill, project/profile policy, docs, and brain-builder tests.
- [x] 4.5 Run `openspec status --change remove-houmao-utils-llm-wiki` and confirm the change is apply-ready.
