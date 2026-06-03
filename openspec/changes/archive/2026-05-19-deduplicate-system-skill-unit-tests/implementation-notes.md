## Coverage Inventory

Managed system-skill assertions are retained at these owning layers:

- Pure policy/helper layer: `tests/unit/agents/test_system_skills.py`
  - Owns parser normalization, payload serialization, invalid mode/selector errors, source/profile resolution, deduplication, disabled selection, exact replacement selection, managed-home sync cleanup, retired path cleanup, and user-skill preservation.
- Recipe parser layer: `tests/unit/agents/test_definition_parser.py`
  - Owns acceptance of `launch.system_skills` in source recipes and rejection of profile-only `inherit` mode in recipe policy.
- Catalog/projection layer: `tests/unit/project/test_catalog.py`
  - Owns persistence of launch-profile `system_skills_payload` and projection of `defaults.system_skills`.
- Runtime/build layer: `tests/unit/agents/test_brain_builder.py`
  - Owns representative wiring from build input to installed managed home/provenance, source additive behavior, profile override/disable behavior, collision rejection, and Gemini projection root.
- Launch forwarding layer: `tests/unit/srv_ctrl/commands/test_agents_core.py`
  - Owns source/profile policy forwarding into `BuildRequest`.
- CLI layer: `tests/unit/srv_ctrl/test_project_commands.py`
  - Owns smoke coverage for the three command lanes: easy specialist, easy profile, and explicit launch profile.

## Duplicate Assertions Removed

- Removed repeated CLI invalid-name and conflict assertions where equivalent selector/mode validation is already owned by pure policy tests and one representative CLI conflict smoke remains.
- Removed plain-output specialist assertion because JSON output and generated recipe payload already prove user-visible policy wiring for that lane.
- Removed easy-profile clear assertion because specialist and explicit launch-profile lanes cover clear wiring, while easy profile keeps create/patch/disable/conflict smoke coverage.
- Removed brain-builder exact filesystem preservation assertions from reused-home disable coverage because `sync_system_skills_for_home` directly owns exact removal and user-skill preservation details.
