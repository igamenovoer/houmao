## Why

Active `Houmao` CAO docs, specs, issue notes, and install/troubleshooting guidance still point at the upstream/orphan CAO source or the ambiguous package-name install. Now that CAO should be treated as a fork-owned external dependency, that guidance no longer makes it clear which repository and executable source `Houmao` expects operators to use.

## What Changes

- Define the `imsight-forks/cli-agent-orchestrator` fork as the canonical CAO source reference for active `Houmao` docs, specs, and implementation-facing notes.
- Replace active references to `extern/orphan/cli-agent-orchestrator` and `awslabs/cli-agent-orchestrator` in `Houmao` operational guidance with fork-oriented references.
- Replace CAO installation guidance that currently uses `uv tool install cli-agent-orchestrator` or upstream Git URLs with a single fork-backed install story.
- Update CAO launcher/demo troubleshooting messages, reference docs, and issue notes so they align with the same fork-backed source/install contract.
- Keep explicitly required provenance or legal-attribution text only where it is intentionally serving historical or licensing purposes.

## Capabilities

### New Capabilities
- `cao-fork-reference-policy`: Defines the canonical fork-backed CAO source/install reference policy for active `Houmao` guidance.

### Modified Capabilities
- `cao-rest-client-contract`: Replace CAO API/profile source-of-truth references so active requirements point at the tracked fork rather than orphan/upstream source locations.
- `cao-server-launcher`: Update launcher install guidance requirements so missing-`cao-server` instructions point users at the fork-backed CAO installation path.
- `cao-server-launcher-demo-pack`: Update demo prerequisite and troubleshooting requirements so launcher tutorial packs reference the fork-backed CAO install flow consistently.

## Impact

- `README.md`
- `docs/reference/`
- `scripts/demo/cao-server-launcher/`
- `src/gig_agents/cao/server_launcher.py`
- `context/issues/known/`
- `openspec/specs/`
