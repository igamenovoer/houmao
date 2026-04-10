## Context

The repository currently has one large fixture root at `tests/fixtures/agents/`, but the codebase no longer treats that root as one coherent source of truth. Current project-aware behavior is catalog-backed `.houmao/` overlays with `.houmao/agents/` as a non-authoritative compatibility projection. Maintained demos already trend toward pack-local tracked `inputs/agents/` trees plus run-local generated working trees, while direct-dir credential CRUD still supports plain filesystem-backed `--agent-def-dir` roots with human-readable auth names and `launch-profiles/`.

That means the current fixture root is overloaded:

- plain direct-dir contract for `--agent-def-dir` tests,
- pseudo-canonical replacement for the current project-overlay compatibility tree,
- local-only auth-bundle storage for demos and smoke flows.

Those lanes now have different directory shapes, naming rules, and ownership models. Continuing to keep them in one tree forces either stale docs or fake compatibility claims.

## Goals / Non-Goals

**Goals:**
- Separate repository fixture families by contract and ownership.
- Give direct-dir tests one maintained fixture root that matches the current plain filesystem contract, including `launch-profiles/`.
- Move local-only credential material into a dedicated fixture family that does not imply a full canonical agent-definition tree.
- Keep maintained project-backed tests and demos aligned with fresh project overlays or demo-owned tracked `inputs/agents/` trees.
- Update maintained fixture guidance so maintainers can quickly tell which fixture lane applies to their workflow.

**Non-Goals:**
- Preserve `tests/fixtures/agents/` as a maintained canonical tree for every workflow.
- Make the plain direct-dir fixture root mimic project-overlay opaque auth bundle refs.
- Update every archival `scripts/demo/legacy/` reference to the new structure as part of the maintained contract.
- Introduce a new generic project fixture authoring system beyond the existing overlay and demo-local patterns.

## Decisions

### Decision: Split fixture families by contract instead of keeping one shared `agents/` tree

The repository will define three distinct maintained fixture lanes:

- `tests/fixtures/plain-agent-def/`
  Secret-free tracked fixture root for explicit plain `--agent-def-dir` tests and helpers.
- `tests/fixtures/auth-bundles/`
  Local-only host credential bundles keyed by tool and bundle name, without any claim that the parent directory is a full canonical agent-definition tree.
- project-overlay or demo-local generated trees
  Fresh `.houmao/` overlays and demo-owned `inputs/agents/` trees remain the maintained source for project-aware and demo-local flows.

Rationale:
- These lanes already exist conceptually in the codebase; making them explicit removes ambiguity.
- One tree cannot honestly model both human-named direct-dir auth bundles and opaque project-overlay auth bundle refs.

Alternatives considered:
- Keep `tests/fixtures/agents/` and merely update its docs: rejected because the directory shape itself is part of the confusion.
- Force every maintained flow to use project overlays only: rejected because direct-dir credential CRUD and some narrow tests still intentionally exercise the plain filesystem lane.

### Decision: The plain direct-dir fixture root stays secret-free and models the plain filesystem contract

`tests/fixtures/plain-agent-def/` will contain the maintained tracked filesystem shape for direct-dir tests:

- `skills/`
- `roles/`
- `presets/`
- `launch-profiles/`
- `tools/<tool>/adapter.yaml`
- `tools/<tool>/setups/<setup>/...`
- `tools/<tool>/auth/` roots for supported tools

When populated locally, plain direct-dir auth bundles continue to use human-readable directory names under `tools/<tool>/auth/<name>/`.
The tracked tree itself remains secret-free; direct-dir tests that need credential contents may create them under copied temp roots or source them from the dedicated local auth-bundle lane when appropriate.

Rationale:
- This matches the current supported direct-dir command contract and credential rename behavior.
- It avoids pretending that the tracked plain-dir fixture is the same as the project-overlay compatibility projection.

Alternatives considered:
- Track opaque bundle refs inside the plain direct-dir fixture: rejected because that would contradict the current direct-dir command semantics.
- Keep auth bundles inline under the tracked fixture root: rejected because that preserves the current overloading and secret-handling confusion.

### Decision: Dedicated auth bundles become the only maintained host-local credential fixture family

`tests/fixtures/auth-bundles/<tool>/<bundle>/...` becomes the maintained local-only credential fixture family for supported demos, smoke flows, and manual helpers.

This lane owns:

- bundled credential files and env payloads,
- the encrypted archive and checksum workflow for local-only credential material,
- named lanes such as Claude `official-login`, Claude `kimi-coding`, Codex `yunwu-openai`, and maintained Gemini auth lanes.

Maintained demos and manual flows that need host-local credentials will refer to this lane directly, then materialize demo-local or run-local aliases as needed.

Rationale:
- Auth bundles are not the same thing as a canonical agent-definition source tree.
- Demos already copy or generate their own tracked secret-free agent trees and only need a local credential source to attach at runtime.

Alternatives considered:
- Keep auth bundles under `tests/fixtures/plain-agent-def/tools/.../auth/`: rejected because it turns the direct-dir fixture root back into a hybrid tracked-plus-local tree.

### Decision: Maintained project-backed flows must stop using the broad repository fixture root

Maintained project-aware tests and demos will use one of two patterns:

- fresh `.houmao/` overlays created during the test or helper run, or
- tracked demo-local `inputs/agents/` trees copied into run-local working directories, with auth aliases materialized from `tests/fixtures/auth-bundles/`.

They will not treat the plain direct-dir fixture root as a substitute for the project-overlay compatibility projection.

Rationale:
- This matches the current code and docs, which already define project overlays as the maintained repo-local model.
- It prevents maintained project-aware paths from quietly inheriting stale direct-dir assumptions.

Alternatives considered:
- Teach demos to consume `tests/fixtures/plain-agent-def/` directly: rejected because it couples unrelated demos to a broad fixture root they do not own.

### Decision: The old `tests/fixtures/agents/` root leaves the maintained contract

The repository will stop using `tests/fixtures/agents/` as a maintained contract surface. The change may leave a short redirect note or transitional stub if needed for migration, but the maintained guidance, tests, and demos will no longer rely on that path as a living source tree.

Rationale:
- Keeping the old path alive as a maintained contract would continue to blur which lane is authoritative.
- Breaking changes are acceptable in this repository when they improve clarity.

Alternatives considered:
- Keep a full compatibility mirror at the old path: rejected because it doubles maintenance cost and invites drift again.

## Risks / Trade-offs

- [Risk] Maintainers with local automation targeting `tests/fixtures/agents/...` will break after the split. → Mitigation: add redirect guidance and update maintained docs and helper constants in the same change.
- [Risk] Moving the encrypted local credential archive may temporarily confuse restore workflows. → Mitigation: keep one clear README in the new auth-bundle root and update archive/checksum filenames together.
- [Risk] Plain direct-dir tests may accidentally rely on ambient `.houmao` discovery if helpers stop passing explicit roots. → Mitigation: keep direct-dir tests explicit about `--agent-def-dir` and use copied temp roots in test helpers.
- [Risk] Legacy demo packs will continue to contain stale references. → Mitigation: treat `scripts/demo/legacy/` as archival and update only maintained surfaces in this change.

## Migration Plan

1. Create `tests/fixtures/plain-agent-def/` with the maintained direct-dir layout and move the tracked role, preset, skill, and setup assets that still belong to that lane.
2. Create `tests/fixtures/auth-bundles/` for local-only credential material and move the encrypted archive, README guidance, and maintained bundle names there.
3. Update maintained demos, manual smoke flows, and their tests to source host-local auth from `tests/fixtures/auth-bundles/` while continuing to build from project overlays or demo-local tracked trees.
4. Update fixture docs and maintained helper constants so they describe the split lanes and stop calling one repository tree canonical for every workflow.
5. Remove maintained references to `tests/fixtures/agents/` or replace that root with a narrow redirect note if a transitional pointer is still useful.

## Open Questions

- Do we want a short redirect README left at `tests/fixtures/agents/`, or should the old root disappear entirely once maintained references are migrated?
