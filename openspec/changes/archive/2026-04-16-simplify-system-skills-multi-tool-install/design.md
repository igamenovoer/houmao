## Context

`houmao-mgr system-skills install` currently accepts one required `--tool` value, repeatable `--set` values for named system-skill bundles, and an optional `--home` override. The CLI command resolves one effective home with `_resolve_effective_system_skills_home()` and then calls the shared `install_system_skills_for_home()` primitive. That shared primitive already owns catalog loading, selection expansion, deduplication, projection mode handling, collision behavior, and filesystem mutation for one concrete tool home.

The requested multi-tool install is a command-shape improvement, not a new installer model. The implementation should keep the shared installer single-tool and single-home so managed launch, managed join, and existing single-tool external installs continue to use the same contract.

## Goals / Non-Goals

**Goals:**

- Let operators install the same selected Houmao system skills into multiple supported tool homes with one command.
- Rename the public named-set selection flag from `--set` to `--skill-set` so command usage says what kind of set is being selected.
- Keep explicit target-home semantics clear by rejecting `--home` whenever `--tool` expands to more than one tool.
- Preserve current single-tool home resolution, explicit home override precedence, selected skill behavior, and JSON payload shape.
- Produce deterministic, testable multi-tool output that identifies each selected tool, resolved home, selected sets, explicit skills, resolved skills, projected relative directories, and projection mode.
- Update user-facing docs so the new shorthand is discoverable without making `--home` look valid for multi-tool installs.

**Non-Goals:**

- Do not change the packaged system-skill catalog, named sets, CLI-default selection, managed launch auto-install, or managed join auto-install.
- Do not preserve `--set` as a supported alias for `--skill-set` in this change.
- Do not add multi-home explicit mapping syntax such as `--home codex=...`.
- Do not make the shared installer transactional across multiple homes.
- Do not add comma-separated tool support to `system-skills status` in this change.

## Decisions

1. Parse comma-separated tools in the CLI layer.

   `install_system_skills_command()` should parse `--tool` into a tuple of tool names before home resolution. The parser should trim whitespace, reject empty entries, reject duplicate tools, and validate every parsed tool against the existing supported-tool table. Keeping this in `srv_ctrl/commands/system_skills.py` avoids leaking multi-target concerns into `houmao.agents.system_skills`.

   Alternative considered: change `install_system_skills_for_home()` to accept multiple tools. That would make the shared installer responsible for home resolution and output aggregation, which is outside its current one-home mutation contract.

2. Treat `--home` as single-tool-only.

   If the parsed tool list contains more than one tool and `--home` is present, the command should fail before any filesystem mutation. The error should explain that omitted `--home` lets each selected tool resolve through its own env/default home rules.

   Alternative considered: apply the same explicit home to all tools. That is unsafe because tools use different visible projection roots, and Gemini's effective home intentionally differs from Claude/Codex/Copilot project defaults.

3. Rename the CLI flag but keep the installer selection model.

   The Click option should become `--skill-set` while the shared installer can continue receiving a tuple of set names. The public flag name changes, but the catalog and `install_system_skills_for_home(set_names=...)` contract do not need to change.

   `--set` should not be kept as a hidden alias. The repository is still in active development, and keeping both names would make docs, help text, and tests carry avoidable ambiguity.

   Alternative considered: keep `--set` as an alias. That would reduce command-line breakage but weakens the requested explicitness and leaves two public spellings for the same concept.

4. Reuse existing selection behavior for each tool.

   The command should compute `use_cli_default = not skill_set_names and not skill_names` and pass the parsed skill-set names to `install_system_skills_for_home(set_names=...)`. The resolved skill list should therefore match existing single-tool behavior for every selected tool.

   A lightweight preflight may call `load_system_skill_catalog()` and `resolve_system_skill_selection()` once before mutation so unknown sets or skills fail before installing into the first home.

5. Preserve current single-tool JSON and plain output.

   When the parsed tool list contains exactly one tool, the command should emit the current payload shape:

   - `tool`
   - `home_path`
   - `selected_sets`
   - `explicit_skills`
   - `resolved_skills`
   - `projected_relative_dirs`
   - `projection_mode`

   When the parsed tool list contains multiple tools, the command should emit an aggregate payload:

   - `tools`: parsed tool names in request order
   - `installations`: one single-tool-shaped result payload per tool

   This keeps existing automation stable while giving new automation one predictable multi-tool envelope.

6. Execute installs sequentially and fail fast.

   The command should install tools in request order. If a filesystem or runtime error occurs for one tool, the command should fail with the existing `ClickException` path, including the underlying error detail. Cross-home rollback is out of scope because the current installer is not transactional and the target homes are independent operator-controlled locations.

## Risks / Trade-offs

- Partial multi-tool install after a later filesystem failure -> Mitigation: preflight parse, tool validation, duplicate validation, home restriction, and selection validation before mutation; document that installs are applied per resolved tool home.
- Existing commands that use `--set` will fail after the rename -> Mitigation: document the breaking rename clearly, update README/reference examples, and add tests that `--skill-set` is the supported spelling.
- Existing scripts expecting a scalar `tool` field -> Mitigation: keep the scalar payload unchanged for single-tool invocations.
- Ambiguous user intent around `--home` -> Mitigation: reject multi-tool plus `--home` with an explicit message and examples that show separate single-tool commands for explicit homes.
- Parser edge cases such as whitespace, empty entries, or duplicates -> Mitigation: cover all parser behavior in unit tests.

## Migration Plan

This change is additive for multi-tool installs and breaking for named-set flag spelling. Operators should replace `--set <name>` with `--skill-set <name>`. Rollback is restoring the old Click option name and removing the comma parser and aggregate payload path; no persistent data migration is required.

## Open Questions

None.
