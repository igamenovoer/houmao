## Why

The repository now documents `skills/`, `roles/`, and `tools/` as the canonical agent-definition layout, but several demo packs, exploration helpers, tests, and specs still depend on legacy `brains/` and `blueprints/` directories. That split keeps migration debt alive, forces pack-owned demo assets to ship duplicate source trees, and makes it unclear which layout is actually authoritative.

## What Changes

- **BREAKING** Remove demo-owned legacy agent-definition subtrees such as `agents/brains/` and `agents/blueprints/` from pack-local `scripts/demo/**/agents` trees that already have canonical `roles/` and `tools/` assets.
- Refactor runtime helpers, demo runners, test fixtures, and scripted preflight checks that still require legacy recipe, blueprint, config-profile, or credential-profile paths so they resolve the current preset/setup/auth layout instead.
- Keep temporary compatibility field names such as `recipe_path`, `brain_recipe_path`, or `blueprint_path` only where they still point at preset-backed launch inputs rather than at legacy source trees.
- Update demo, fixture, and getting-started documentation so the documented operator contract consistently uses `roles/`, `tools/`, `setups/`, `auth/`, and preset-backed launch examples.
- Align OpenSpec requirements that still codify `brains/`, `blueprints/`, `cli-configs/`, or `api-creds/` as current source-of-truth behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `component-agent-construction`: tighten the canonical agent-definition contract so tracked source trees and downstream consumers no longer depend on legacy recipe/blueprint layouts.
- `demo-agent-launch-recovery`: extend the recovery contract from startup-only compatibility to removal of legacy source-tree dependencies in affected demo and tutorial launch helpers.
- `claude-code-state-tracking-interactive-watch`: require the interactive watch workflow to build from canonical preset-backed fixture inputs rather than `tests/fixtures/agents/brains/`.
- `mail-ping-pong-gateway-demo-pack`: require the pack's tracked startup inputs and operator-facing docs to use canonical preset/setup/auth paths instead of recipe-era terminology.
- `mailbox-roundtrip-tutorial-pack`: require default participant configuration and tutorial guidance to resolve canonical presets rather than legacy blueprints.
- `houmao-server-agent-api-live-suite`: require the pack-owned `agents/` tree to publish only the canonical layout needed for its tracked selectors and auth-backed launch inputs.
- `passive-server-parallel-validation`: require the Step 7 demo pack's `agents/` tree to publish only the canonical layout needed for its tracked selectors and auth-backed launch inputs.
- `runtime-agent-dummy-project-fixtures`: move tracked reusable skill-fixture requirements off `tests/fixtures/agents/brains/skills/` and onto the canonical `skills/` tree.
- `docs-getting-started`: replace the old agent-definition directory description with the canonical preset/setup/auth layout only.
- `cao-rest-client-contract`: replace credential-profile path requirements that still reference `agents/brains/api-creds/` with the canonical `agents/tools/<tool>/auth/` layout.

## Impact

- Affected code: demo launch helpers, pack-local `scripts/demo/**/agents` trees, exploration harnesses, runtime/test fixture builders, and legacy realm-controller compatibility surfaces.
- Affected docs: fixture READMEs, demo READMEs, getting-started guides, and any operator guidance that still names `brains/`, `blueprints/`, `cli-configs/`, or `api-creds/` as current.
- Affected tests: integration and unit suites that seed legacy fixture trees or assert legacy `--blueprint` / recipe-path behavior.
- Affected users: maintainers or local operators who still point demo scripts or internal tests at old-style agent-definition paths will need to switch to canonical preset-backed inputs.
