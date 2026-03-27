## ADDED Requirements

### Requirement: Pack-owned agent assets use canonical layout only
The pack-owned `scripts/demo/passive-server-parallel-validation-demo-pack/agents/` tree SHALL publish its tracked selector, role, setup, and auth-backed launch assets through the canonical agent-definition layout only.

That pack-owned tree SHALL keep tracked launch assets under `roles/`, `tools/`, and optional `skills/` or `compatibility-profiles/` when needed, and SHALL NOT ship tracked `brains/` or `blueprints/` directories as source-of-truth launch inputs for the Step 7 demo pack.

#### Scenario: Maintainer inspects the pack-owned agent tree
- **WHEN** a maintainer inspects `scripts/demo/passive-server-parallel-validation-demo-pack/agents/`
- **THEN** the tracked selector and launch assets live under canonical `roles/` and `tools/` paths
- **AND THEN** the pack does not ship tracked legacy `brains/` or `blueprints/` directories for those same launch assets

#### Scenario: Pack preflight resolves pack-owned launch inputs without legacy directories
- **WHEN** the demo pack validates its tracked provider prerequisites
- **THEN** it resolves the required preset, setup, auth, adapter, and role assets from the pack-owned canonical layout
- **AND THEN** successful preflight does not require pack-local legacy `agents/brains/` or `agents/blueprints/` directories
