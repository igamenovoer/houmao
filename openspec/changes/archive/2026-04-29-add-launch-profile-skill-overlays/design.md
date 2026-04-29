## Context

Project skills currently have one canonical registration surface under `project skills`, and specialists or recipes select skills by name from the projected project skill tree. Launch profiles share a catalog family across explicit recipe-backed profiles and easy specialist-backed profiles, but they currently store launch defaults rather than skill overlays.

The target behavior is more flexible than name-only profile skill references, but still keeps the shared project skill repository clean. A launch profile can add registered project skills by name, or it can carry private path-backed skills that are copied or symlinked directly into the built agent home only during launches from that profile. Private skill paths are not imported into `.houmao/content/skills/`, are not visible in `project skills list`, and are not protected by the project skill registry lifecycle except through the launch profile that owns them.

## Goals / Non-Goals

**Goals:**

- Let explicit launch profiles and easy profiles add profile-owned skills without mutating the source specialist or recipe.
- Support registered project skill references through `--add-registered-skill` and `--remove-registered-skill`.
- Support profile-private path skills through `--add-private-skill`, `--add-private-skill-symlink`, and `--remove-private-skill`.
- Keep private path-backed skills out of the project skill repository and compatibility projection.
- Preserve existing project skill registration semantics for registered skill names.
- Make private skill directory names override registered or source skills with the same installed skill name.
- Record profile skill overlays in profile inspection, projection YAML, and launch provenance.

**Non-Goals:**

- Add arbitrary path skills to source recipes or specialists.
- Add a new project skill ingestion path through launch-profile commands.
- Add per-registered-skill mode selection; registered skill projection remains owned by the existing project skill contract.
- Provide one-shot launch CLI skill injection on `agents launch` or `project easy instance launch`.

## Decisions

1. Store registered and private profile skills separately.

   Launch profiles should distinguish shared project skill references from private path-backed sources. Registered refs are stored by skill name. Private refs are stored as source path, derived installed name, and mode (`copy` or `symlink`). This avoids overloading a single string list with ambiguous meanings.

   Alternative considered: store all entries as a single mixed list. That makes projection and removal harder to reason about, especially for `--remove-private-skill <path>` and private-over-registered precedence.

2. Add normalized catalog tables rather than JSON-only payloads.

   The project catalog should use relation tables for profile-to-registered-skill refs and profile-to-private-skill refs. This enables removal protection for registered skills, deterministic ordering, and structured loading without parsing nested JSON for referential integrity. Projection YAML can still render these rows as `defaults.skills`.

   Alternative considered: store the full overlay as JSON in `launch_profiles`. That is easier initially but weakens validation and makes project-skill removal checks less direct.

3. Derive private installed skill names from path basenames.

   `--add-private-skill <path>` and `--add-private-skill-symlink <path>` take only a path, so the installed skill name should be the final directory name. The path must point to a directory containing `SKILL.md`, and the derived name must satisfy project catalog name rules.

   Alternative considered: require `name=path`. The current requested CLI avoids that extra syntax, and basename derivation is predictable enough when duplicate private basenames are rejected.

4. Resolve and store private paths predictably.

   Relative private paths should resolve against the active project root at storage time. When the resolved path is under the project root, store a project-relative spelling for projection readability and portability; otherwise store the absolute path. `--remove-private-skill <path>` should normalize the supplied path the same way before matching stored rows.

   Alternative considered: store raw CLI strings. That makes remove matching fragile and makes launches depend on the caller's current directory.

5. Apply private skills after registered skills during brain-home construction.

   The launch flow should build an effective registered skill list from source preset skills plus profile registered skills, then pass private projections separately into brain construction. `build_brain_home` should project registered skills through the existing path first and then project private skills to the same skill destination, replacing any same-name destination. This implements private-over-registered precedence without changing registered skill validation.

   Alternative considered: remove private-shadowed registered names before build. That reduces work but hides useful provenance and can change source validation behavior.

## Risks / Trade-offs

- Private symlink sources can move or disappear -> Validate private skill paths at profile write time and again at launch time with clear errors.
- Private path skills reduce reproducibility compared with registered project skills -> Use copy mode by default and make symlink mode explicit through `--add-private-skill-symlink`.
- Private-over-registered precedence can surprise operators -> Report both registered and private overlays in profile inspection and launch provenance, including private shadowed names.
- Catalog schema changes require migration care -> Add tables with `CREATE TABLE IF NOT EXISTS` and avoid rewriting existing launch-profile rows.
- Path normalization can be confusing for remove operations -> Match removals against normalized resolved paths and include stored paths in `get` output.
