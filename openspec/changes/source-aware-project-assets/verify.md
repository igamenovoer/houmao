# Verification Notes

Date: 2026-04-21

## Commands Run

```bash
pixi run pytest tests/unit/project/test_catalog.py tests/unit/srv_ctrl/test_project_commands.py -q
pixi run ruff check \
  tests/unit/srv_ctrl/test_project_commands.py \
  src/houmao/project/catalog.py \
  src/houmao/project/migration.py \
  src/houmao/srv_ctrl/commands/project.py \
  src/houmao/srv_ctrl/commands/project_common.py \
  src/houmao/srv_ctrl/commands/project_easy.py \
  src/houmao/srv_ctrl/commands/project_migrate.py \
  src/houmao/srv_ctrl/commands/project_skills.py
pixi run ruff format --check tests/unit/srv_ctrl/test_project_commands.py
```

## Targeted Coverage

- `test_project_catalog_projects_copy_and_symlink_registered_skills`
  Validates canonical project-skill registration in both `copy` and `symlink` modes and confirms `.houmao/agents/skills/` is rebuilt as derived symlink projection.
- `test_project_catalog_reports_broken_symlinked_skill_targets`
  Confirms projection fails loudly when a symlink-backed project skill points at a missing source directory.
- `test_project_migrate_plans_and_applies_supported_legacy_overlay`
  Covers one end-to-end `project migrate` conversion path, including legacy easy-specialist import, canonical project-skill creation, derived projection rebuild, and removal of replaced legacy specialist metadata.
- `test_project_easy_instance_launch_uses_registered_project_skill_projection`
  Covers specialist launch flows in both `copy` and `symlink` modes. The `copy` lane keeps the canonical snapshot content even after the original source changes, while the `symlink` lane exposes the updated live source content at launch time.
- `test_project_easy_instance_launch_reloads_symlink_project_skill_after_source_edit`
  Covers repeated launches after a symlink-backed project skill source edit and confirms later launches see the updated skill content through the derived projection.

## Result

- Targeted project catalog and CLI tests passed: `123 passed`.
- Targeted Ruff lint passed.
- Targeted Ruff format check passed for the touched Python test file.
