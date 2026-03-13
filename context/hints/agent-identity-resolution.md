# Agent Identity Resolution (Historical Snapshot)

## Purpose
Document the resolution flow referenced by archived OpenSpec discussions for
agent identity handling in `gig_agents.agents.realm_controller`.

## Resolution Flow
1. Classify input as manifest path vs agent identity token.
2. Validate the selected mode-specific constraints.
3. Canonicalize identity/path form.
4. Resolve tmux session identity when name-based mode is used.
5. Load and validate the persisted session manifest.

## Notes
This file is a localized historical-support snapshot added during OpenSpec
archive normalization so archived references remain repository-local.
