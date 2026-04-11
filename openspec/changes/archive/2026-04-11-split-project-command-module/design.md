## Context

`src/houmao/srv_ctrl/commands/project.py` is currently a single roughly 5,000-line Click command module. It contains the public `project_group`, project overlay bootstrap/status commands, project-scoped credential group registration, `project agents tools`, roles, presets/recipes, explicit launch profiles, easy profiles, easy specialists, easy instances, project mailbox commands, launch-profile storage helpers, specialist payload helpers, runtime instance payload helpers, model/prompt/mailbox helper code, and some credential helper code that appears to have been superseded by `commands/credentials.py`.

The top-level CLI imports `project_group` from `houmao.srv_ctrl.commands.project`, and tests currently monkeypatch helper paths such as `houmao.srv_ctrl.commands.project._ensure_project_overlay`. The refactor therefore needs to reduce module size without turning the public import path into a sudden breaking change.

The desired end state is:

```text
houmao.srv_ctrl.commands.project
  public entrypoint, project_group registration, init/status

houmao.srv_ctrl.commands.project_common
  overlay resolution and shared CLI helper functions

houmao.srv_ctrl.commands.project_tools
  project agents tools ...

houmao.srv_ctrl.commands.project_definitions
  project agents roles/presets/recipes ...

houmao.srv_ctrl.commands.project_launch_profiles
  project agents launch-profiles ...

houmao.srv_ctrl.commands.project_easy
  project easy profile/specialist/instance ...

houmao.srv_ctrl.commands.project_mailbox
  project mailbox ...
```

## Goals / Non-Goals

**Goals:**

- Reduce `project.py` into a small public entrypoint and command registration module.
- Move project command families into focused modules with clear ownership boundaries.
- Move shared helpers into one or more explicit shared modules instead of leaving a large anonymous helper tail.
- Preserve the current `houmao-mgr project ...` CLI shape, output payloads, failure behavior, and project-aware bootstrap behavior.
- Preserve `houmao.srv_ctrl.commands.project.project_group` as the stable import used by `commands/main.py`.
- Keep the refactor staged so behavior regressions can be isolated by command family.
- Remove dead project-local helper code only after confirming there are no runtime callers.

**Non-Goals:**

- Do not change project catalog schemas, projection formats, launch-profile semantics, credential semantics, or mailbox storage.
- Do not introduce a new CLI framework or change Click command names.
- Do not convert `houmao.srv_ctrl.commands.project` into a package in the first pass.
- Do not reorganize the broader non-project command tree.
- Do not intentionally preserve private helper monkeypatch paths beyond what tests require during migration.

## Decisions

### Keep `project.py` as the public entrypoint

Keep `src/houmao/srv_ctrl/commands/project.py` as the module imported by `commands/main.py`, and have it register command groups imported from new sibling modules.

Rationale: this avoids a high-churn `project.py` to `project/` package conversion and preserves the stable public import of `project_group`. It also lets implementation move in small slices without requiring all tests to update at once.

Alternative considered: replace `project.py` with a `commands/project/` package. That is a cleaner long-term namespace, but it is riskier because Python cannot have both a `project.py` module and a `project/` package at the same import location. That approach would force a larger atomic rename and broader import-path migration.

### Split by command family first

Extract command groups by the CLI tree they own:

- `project_tools.py` owns `project agents tools ...`
- `project_definitions.py` owns `project agents roles ...`, `project agents presets ...`, and `project agents recipes ...`
- `project_launch_profiles.py` owns `project agents launch-profiles ...` and launch-profile storage/payload helpers
- `project_easy.py` owns `project easy profile ...`, `project easy specialist ...`, and `project easy instance ...`
- `project_mailbox.py` owns `project mailbox ...`
- `project_common.py` owns shared overlay resolution, name validation, yaml helpers, prompt/model helpers, and small shared payload helpers

Rationale: command-family extraction mirrors the visible CLI tree, gives each module a clear reason to change, and keeps review diffs understandable.

Alternative considered: split purely by helper domain first. That would reduce helper tail size, but it would leave the Click command registration body large and continue to mix unrelated command families.

### Extract launch-profile helpers with the launch-profile command module

Move `_store_launch_profile_from_cli`, launch-profile payload builders, prompt overlay resolution, profile mailbox resolution, posture mapping, memory-dir option resolution, managed-header policy conversion, and related helpers with `project_launch_profiles.py`.

Rationale: explicit launch profiles and easy profiles both use this logic, but the explicit launch-profile command family is the narrower owner of the reusable storage abstraction. `project_easy.py` can import this helper surface instead of duplicating it.

Alternative considered: put these helpers in `project_common.py`. That would make `project_common.py` too broad and recreate the same shared-helper dumping ground in a new file.

### Keep easy workflows together initially

Keep easy profiles, easy specialists, and easy instances in one `project_easy.py` module during the first split.

Rationale: those flows share specialist metadata, auth selection, profile defaults, and launch/runtime payload logic. A single easy module is still a major improvement over the current file, and it can be split further later if it remains too large.

Alternative considered: create `project_easy_profiles.py`, `project_easy_specialists.py`, and `project_easy_instances.py` immediately. That may be the eventual shape, but doing it in the first pass increases import churn and makes it harder to distinguish behavior regressions from mechanical movement.

### Treat unused credential helper code as a deletion candidate

Before moving the credential helper cluster currently living in `project.py`, confirm whether helpers such as `_run_claude_auth_write`, `_run_codex_auth_write`, `_run_gemini_auth_write`, `_write_project_auth_bundle`, and `_ensure_specialist_auth_bundle` have runtime callers. If they remain unused after the existing `ensure_specialist_credential_bundle` path is confirmed, delete them instead of moving them.

Rationale: moving dead code preserves the very maintenance burden this refactor is meant to reduce.

Alternative considered: move all helper code mechanically first. That is safer if call analysis is uncertain, but it misses a low-risk shrink opportunity.

### Preserve behavior with CLI shape and focused command tests

Run help-shape checks and focused project-command tests after each meaningful extraction. The minimum evidence should include project help shape, project agents/easy/mailbox subcommand help shape, and the existing unit tests covering project command behavior.

Rationale: this is a behavior-preserving refactor; tests should prove command registration, option surfaces, structured payloads, and expected failure wording survive the module split.

## Risks / Trade-offs

- Private test monkeypatch paths may break when helpers move -> Update tests to patch behavior at the new owning module where needed, and keep `project.py` exposing only intentionally stable public names.
- Circular imports may appear between `project_easy.py`, `project_launch_profiles.py`, and `project_common.py` -> Keep shared primitives in `project_common.py`, keep launch-profile storage helpers in `project_launch_profiles.py`, and avoid importing command groups from helper modules.
- `project_common.py` could become a new oversized utility module -> Move only genuinely cross-family helpers there; leave family-specific helpers with their owning command module.
- Click command registration can silently drop commands if groups are imported or added in the wrong order -> Add CLI shape tests and manually inspect `houmao-mgr project --help` plus relevant subgroup help.
- Dead-code deletion can be unsafe if dynamic callers exist -> Use repository search and focused tests before deletion; if uncertain, move first and delete in a follow-up.
- A single large refactor commit may be hard to review -> Implement in staged slices, keeping each slice behavior-preserving and testable.

## Migration Plan

1. Establish a baseline with focused project command tests and help-shape checks.
2. Identify and remove confirmed-dead credential helper code, or defer deletion if caller analysis is inconclusive.
3. Extract `project_common.py` with overlay resolution and narrow shared helpers.
4. Extract `project_mailbox.py`, because it mostly delegates to `mailbox_support` and has limited coupling.
5. Extract `project_launch_profiles.py`, including shared launch-profile storage helpers used by easy profiles.
6. Extract `project_easy.py`, importing the launch-profile helpers instead of duplicating them.
7. Extract `project_tools.py` and `project_definitions.py`.
8. Leave `project.py` as the root group and import/registration entrypoint.
9. Run focused unit tests, CLI shape tests, Ruff, and mypy if the moved helper types create cross-module typing risk.

Rollback is straightforward because this is a local source refactor: revert the extraction commit or move one command family back into `project.py` if a module boundary proves too tangled.

## Open Questions

- Should tests continue to monkeypatch private helper paths through `houmao.srv_ctrl.commands.project`, or should they be migrated to the new owner modules as each helper moves?
- Should the first implementation pass split `project_easy.py` further if it remains above roughly 1,000 lines after extraction?
- Should the archive/sync follow-up add a repository guideline for maximum command module size, or is this change intentionally limited to the current `project.py` pain point?
