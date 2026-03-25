## Context

The interactive full-pipeline demo pack currently publishes `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents/` as if it were a demo-owned native asset tree. In practice, the repository already maintains the canonical tracked launch assets for `gpu-kernel-coder` and related roles under `tests/fixtures/agents/`, so the demo copy creates duplicate maintenance and a real risk of the selector, role, or adapter content drifting.

This change is narrow but crosses spec, docs, tracked filesystem layout, and demo coverage. The runtime launch flow already consumes an agent-definition root from a path, so the main design choice is how the repository should expose that path without continuing to curate two independent trees.

## Goals / Non-Goals

**Goals:**

- Keep the operator-facing demo path `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents` stable.
- Remove the separately maintained demo-owned agent-definition tree and reuse the canonical fixture tree.
- Update the demo contract, documentation, and automated coverage so they describe and verify the symlinked layout explicitly.

**Non-Goals:**

- Redesign the demo startup flow, selector choice, provider handling, or route usage.
- Generalize this pattern to every demo pack in the repository.
- Hide that the shared asset source lives under `tests/fixtures/agents/`; for this repo-owned demo, that coupling is intentional.

## Decisions

### Decision 1: The demo-owned `agents` entry becomes a tracked relative symlink

`scripts/demo/houmao-server-interactive-full-pipeline-demo/agents` will remain the path used by the demo pack, but the repository will store it as a symlink that resolves to `tests/fixtures/agents/`.

Rationale:

- The demo keeps the same operator-facing path and does not need code changes just to point at a different root.
- The repository stops curating a second copy of recipes, tool adapters, configs, and roles for the same launch selector.
- A tracked relative symlink is reviewable in git and works with ordinary repository checkouts.

Alternatives considered:

- Point the demo implementation directly at `tests/fixtures/agents/`: rejected because it leaks an implementation-specific path into more code and docs when the demo already has a local `agents` entry.
- Copy fixture assets into the demo tree during startup: rejected because it preserves duplication and adds runtime mutation to a static demo contract.

### Decision 2: The spec and README will describe shared fixture-backed assets as the supported contract

The demo contract will stop claiming that startup depends on a demo-owned non-test asset tree. Instead, the contract will say the demo ships a local `agents` path whose tracked symlink resolves to the canonical fixture tree.

Rationale:

- The current spec explicitly forbids `tests/fixtures/agents/`, so the contract itself must change rather than relying on an implementation-only patch.
- README wording must match the actual repository layout to avoid misleading maintainers inspecting the demo pack.

Alternatives considered:

- Leave the existing spec language and treat the symlink as an implementation detail: rejected because the current requirement text would become false.

### Decision 3: Coverage will verify the symlinked layout, not just path existence

Demo-focused tests and layout assertions will verify that the demo `agents` path exists and resolves to the tracked fixture tree instead of only checking that some directory is present.

Rationale:

- A plain existence check would allow the repository to drift back to a copied tree without tripping the intended contract.
- This change is primarily about asset ownership and source-of-truth, so tests should lock that down directly.

Alternatives considered:

- Rely only on README/spec updates: rejected because the filesystem contract is easy to regress silently.

## Risks / Trade-offs

- [The demo now depends on a path under `tests/`] → Accept the coupling because this is a repo-owned maintainer demo and `tests/fixtures/agents/` is already the canonical tracked asset source.
- [Relative symlinks can break if the demo directory is moved] → Use a repository-relative tracked symlink and keep a test that resolves the target path.
- [Fixture updates could change demo behavior incidentally] → Keep the demo pinned to the same selector and provider expectations, and let shared fixture reviews cover intentional asset changes in one place.

## Migration Plan

1. Replace the tracked demo `agents/` directory with a symlink to `tests/fixtures/agents/`.
2. Update demo README text and spec language so they describe the symlinked fixture-backed contract.
3. Update demo tests to assert both path presence and symlink target resolution.
4. Verify the demo still launches through its unchanged local `agents` path.

## Open Questions

No open questions remain for the proposal stage.
