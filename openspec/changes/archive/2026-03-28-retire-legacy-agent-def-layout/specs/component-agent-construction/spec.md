## ADDED Requirements

### Requirement: Supported tracked agent-definition trees omit legacy layout mirrors
Repository-owned tracked agent-definition trees that remain part of the supported live system contract SHALL publish launchable source definitions through the canonical `skills/`, `roles/`, `tools/`, and optional `compatibility-profiles/` layout only.

Supported tracked trees SHALL NOT require or ship legacy `brains/`, `brain-recipes/`, `cli-configs/`, `api-creds/`, or `blueprints/` directories as parallel source-of-truth mirrors for the same launchable assets.

Archived historical material under `scripts/demo/legacy/` is not part of that supported live contract and does not define the maintained source-layout requirement.

#### Scenario: Maintainer inspects a supported repo-owned agent-definition tree
- **WHEN** a maintainer inspects a supported repo-owned agent-definition tree used by live fixtures, tests, or non-archived workflows
- **THEN** launchable role, preset, setup, auth, and skill assets live under the canonical `skills/`, `roles/`, `tools/`, and optional `compatibility-profiles/` directories
- **AND THEN** the tree does not ship tracked legacy mirror directories for the same launchable assets

#### Scenario: Canonical consumers do not need legacy directories
- **WHEN** selector resolution, brain construction, or supported live helper logic consumes a tracked repo-owned agent-definition tree
- **THEN** it resolves canonical preset, setup, auth, role, and skill inputs from that tree
- **AND THEN** successful resolution does not require legacy `brains/` or `blueprints/` directories to exist alongside the canonical source layout
