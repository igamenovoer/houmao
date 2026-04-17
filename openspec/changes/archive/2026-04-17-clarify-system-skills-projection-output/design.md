## Context

`houmao-mgr system-skills install` already computes the correct home-relative projection paths for every selected tool and returns those paths in structured output as `projected_relative_dirs`. The plain renderer for multi-tool installs currently prints only `tool: home_path`, which is enough for Claude, Codex, and Copilot because their projection root is `<home>/skills/`, but not enough for Gemini because its effective home is the project root and its projection root is `<home>/.gemini/skills/`.

The installer should remain the source of truth for projection paths. This change should make the command output expose that existing information clearly, not change where skills are installed.

## Goals / Non-Goals

**Goals:**

- Make plain `system-skills install` output show where skills were actually projected for each selected tool.
- Make Gemini output unambiguous by showing `.gemini/skills` as the installed skill root or by listing representative projected paths.
- Preserve the existing JSON fields and installation semantics.
- Keep the display logic derived from existing structured payload data so future tool-specific roots do not require special-case prose.
- Update tests and docs to describe effective homes separately from projection roots.

**Non-Goals:**

- Do not change Gemini's install destination, effective home resolution, or `.agents/skills` behavior.
- Do not add migration or compatibility logic for older installed skills.
- Do not redesign the system-skill catalog, selection rules, or projection modes.
- Do not remove existing structured output fields.

## Decisions

1. Render projection information from `projected_relative_dirs`.

   The structured install payload already contains every projected skill path relative to the effective home. The plain renderer can derive either a common projection root, such as `.gemini/skills`, or print a concise sample/list of projected paths from that field. This avoids duplicating tool-destination rules in the CLI renderer and keeps the output consistent with the actual installer result.

   Alternative considered: add a Gemini-specific note whenever `tool == "gemini"`. That would address the reported confusion but would create a one-off branch and leave future non-`skills/` tools vulnerable to the same problem.

2. Preserve effective home as a first-class output concept.

   The output should continue to report `home_path` because it matters for status/uninstall commands and for environment override debugging. The improvement is to add projection context, not replace home reporting.

   Alternative considered: change Gemini's displayed home to `<home>/.gemini`. That would make the immediate install message less confusing but would be inaccurate because the effective Gemini home remains the project root for home resolution.

3. Keep structured JSON backward-compatible.

   Existing JSON consumers already have `projected_relative_dirs`. If implementation needs an explicit `projection_root` or `projected_roots` field, it should be additive. Existing fields should retain their current names and meanings.

   Alternative considered: replace `home_path` in JSON with a projection path. That would break callers and blur the distinction the system depends on.

## Risks / Trade-offs

- Output verbosity increases for multi-tool installs -> Mitigate by showing a compact projection root or a short "skills under" line rather than listing every installed skill when many skills are selected.
- Root derivation can be wrong if projected paths do not share a common parent -> Mitigate by falling back to representative projected paths or listing all projected paths when the common root cannot be computed cleanly.
- Tests may become too tied to exact wording -> Mitigate by asserting the important substrings and structured payload fields rather than every line of prose.

## Migration Plan

No data migration is required. The change is deployable as a CLI output improvement. Rollback is the previous renderer behavior; installed skill layouts remain unchanged either way.

## Open Questions

- None.
