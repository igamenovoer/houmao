## 1. Catalog Model

- [x] 1.1 Add catalog schema tables for launch-profile registered skill refs and private skill refs with deterministic ordinal ordering.
- [x] 1.2 Extend launch-profile catalog entry models to expose registered skill names, private skill entries, and resolved private source paths.
- [x] 1.3 Add catalog helpers to validate, add, remove, load, and render launch-profile skill overlays without mutating project skill registrations.
- [x] 1.4 Update project skill removal checks to block registered launch-profile refs and ignore private path-backed refs.

## 2. CLI Surfaces

- [x] 2.1 Add `--add-registered-skill` and `--remove-registered-skill` to explicit launch-profile add/set flows.
- [x] 2.2 Add `--add-private-skill`, `--add-private-skill-symlink`, and `--remove-private-skill` to explicit launch-profile add/set flows.
- [x] 2.3 Add the same registered/private skill overlay options to easy profile create/set flows.
- [x] 2.4 Validate registered skill existence, private `SKILL.md` paths, add/remove conflicts, and duplicate private installed names before profile mutation.
- [x] 2.5 Update launch-profile get/list payloads and projection YAML to report registered and private skill overlays.

## 3. Launch And Build

- [x] 3.1 Resolve launch-profile registered and private skill overlays for explicit and easy profile-backed launch.
- [x] 3.2 Extend managed launch plumbing to pass registered skill additions and private skill projections into brain construction.
- [x] 3.3 Extend brain-home construction to copy or symlink private profile skills into the tool skill destination after registered skill projection.
- [x] 3.4 Enforce private-over-registered precedence for installed skill names in the built agent home.
- [x] 3.5 Record registered refs, private refs, and private-shadowed skill names in launch construction provenance.

## 4. Tests

- [x] 4.1 Add catalog and CLI tests for storing, patching, projecting, and inspecting explicit launch-profile skill overlays.
- [x] 4.2 Add catalog and CLI tests for storing, patching, projecting, and inspecting easy-profile skill overlays.
- [x] 4.3 Add tests that private path skills do not appear in `project skills list` or `.houmao/content/skills/`.
- [x] 4.4 Add tests for registered project skill removal protection and private-name non-protection.
- [x] 4.5 Add launch/build tests for registered merge, private copy, private symlink, private-over-registered precedence, and missing private source failures.

## 5. Verification

- [x] 5.1 Run focused project catalog, project command, managed launch, and brain builder unit tests.
- [x] 5.2 Run `pixi run lint`.
- [x] 5.3 Run `pixi run typecheck`.
