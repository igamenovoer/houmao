## ADDED Requirements

### Requirement: Tracked agent-definition trees omit legacy layout mirrors
Repository-owned tracked agent-definition trees SHALL publish launchable source definitions through the canonical `skills/`, `roles/`, `tools/`, and optional `compatibility-profiles/` layout only.

Tracked trees SHALL NOT require or ship legacy `brains/`, `brain-recipes/`, `cli-configs/`, `api-creds/`, or `blueprints/` directories as parallel source-of-truth mirrors for the same launchable assets.

#### Scenario: Maintainer inspects a tracked repo-owned agent-definition tree
- **WHEN** a maintainer inspects a tracked repo-owned agent-definition tree used by Houmao demos, fixtures, or tests
- **THEN** launchable role, preset, setup, auth, and skill assets live under the canonical `skills/`, `roles/`, `tools/`, and optional `compatibility-profiles/` directories
- **AND THEN** the tree does not ship tracked legacy mirror directories for the same launchable assets

#### Scenario: Canonical consumers do not need legacy directories
- **WHEN** selector resolution, brain construction, or demo preflight consumes a tracked repo-owned agent-definition tree
- **THEN** it resolves canonical preset, setup, auth, role, and skill inputs from that tree
- **AND THEN** successful resolution does not require legacy `brains/` or `blueprints/` directories to exist alongside the canonical source layout
