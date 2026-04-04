## Why

The repository now documents `skills/`, `roles/`, and `tools/` as the canonical agent-definition layout, but the current `scripts/demo/` surface still carries old demo-pack assumptions, legacy `brains/` / `blueprints/` references, and a large OpenSpec/test/doc footprint that treats those demos as maintained product surface.

That is now the wrong contract. These demos are about to be redesigned. Until then, they should stop blocking refactors of the live systems. Keeping them as current runnable/spec'd workflows forces the repo to preserve obsolete launch paths, fixture shapes, and docs.

## What Changes

- **BREAKING** Move the current `scripts/demo/*` demo packs under `scripts/demo/legacy/` as historical reference material rather than maintained operator surface.
- Remove the current demo-pack capability specs from `openspec/specs/` and strip cross-cutting requirements that still make current demos normative for the live system.
- Remove or demote tests, docs, and helper surfaces that treat archived demos as supported workflows.
- Continue simplifying live shared fixtures and docs around the canonical `skills/`, `roles/`, `tools/`, `setups/`, and `auth/` layout where those surfaces remain part of the maintained system.
- Retire the legacy encrypted fixture snapshot at `tests/fixtures/agents/brains/api-creds.tar.gz.gpg` and standardize on the existing canonical `tests/fixtures/agents/tools.tar.gz.enc` archive for local-only auth bundles.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `component-agent-construction`: scope the canonical tracked agent-definition contract to supported live source trees rather than archived demo history.
- `demo-agent-launch-recovery`: retire the current “repair and preserve old demo startup” obligation so archived demos stop constraining the active system contract.
- `claude-code-state-tracking-interactive-watch`: keep the live explore workflow on canonical preset-backed fixture inputs rather than legacy `brains/` paths.
- `runtime-agent-dummy-project-fixtures`: keep reusable non-demo probe fixtures and canonical skill-fixture layout without requiring the archived skill-invocation demo-pack contract.
- `docs-getting-started`: keep the getting-started contract focused on supported current system surfaces and canonical agent-definition layout.
- `cao-rest-client-contract`: remove the current live demo tutorial-pack requirement from the maintained system contract.
- `docs-stale-content-removal` and related doc contracts: stop presenting archived demos as supported workflows.

The change also removes the current demo-pack capability specs and companion demo-support specs that only exist to preserve `scripts/demo/*` as maintained behavior.

## Impact

- Affected code: `scripts/demo/*`, demo-support modules under `src/houmao/demo/`, any helpers that hardcode supported `scripts/demo/*` paths, and shared live fixture/explore surfaces that still reference legacy agent-definition layout.
- Affected specs: direct demo-pack capability specs, demo companion specs, and cross-cutting capabilities that still require demos as part of the maintained system contract.
- Affected docs/tests: demo READMEs, reference docs, manual/unit demo tests, and workflow notes that still present archived demos as supported surfaces.
- Affected users: maintainers who still rely on the current demo packs as runnable workflows will now treat them as historical reference under `scripts/demo/legacy/` until redesigned replacements exist.
