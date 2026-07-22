## Why

Houmao currently marks both actor entrypoints as explicit-only, so natural operator and managed-agent requests cannot reliably enter the actor-specific router that was designed to establish posture and delegate work safely. The admin welcome skill is implicitly eligible at the same time, creating competing ownership for informational Houmao requests, while the behavior-testing catalog does not distinguish manual and automatic invocation accurately.

## What Changes

- Change `houmao-admin-entrypoint` and `houmao-agent-entrypoint` to actor-scoped narrow implicit invocation for any request whose subject or requested outcome concerns Houmao, including informational questions, incomplete tasks, and operational work.
- Make `houmao-admin-welcome` explicit-only and strictly manual: only an explicit `$houmao-admin-welcome ...` prompt invokes it, while the admin entrypoint may recommend that command but never delegates to welcome automatically.
- Give both entrypoints an explicit intent-classification phase. Informational requests are answered locally without target discovery or sibling loading; agent informational requests also skip managed-self identity verification.
- Require fresh managed-self identity verification after a request is classified as operational and before the agent entrypoint selects or delegates a substantive route.
- Preserve explicit invocation precedence for welcome, shared routines, and loop skills. Keep shared routines, pro loop, and lite loop explicit-only as initial roots while allowing entrypoint-to-sibling delegation.
- Preserve the deployment boundary: operators manually install the admin pack, while managed launch and join install the agent pack.
- Extend `houmao-dev-behavior-testing` with manual and automatic driver-invocation metadata, selectors, frozen run provenance, reporting, and integrity checks.
- Add automatic positive cases for informational and operational entrypoint phases, shared and loop delegation, and combined-pack actor disambiguation; revise stale welcome, admin, and loop oracles; preserve manual direct-root coverage.
- Advance the behavior catalog version and increment only case revisions whose stimuli, expected roots, routes, or semantic oracles change.

## Capabilities

### New Capabilities

- `houmao-system-skill-entrypoint-activation`: Defines broad actor-scoped implicit entrypoint discovery, strict manual welcome invocation, informational and operational phases, explicit sibling boundaries, and unchanged admin-versus-managed deployment ownership.
- `houmao-dev-behavior-testing-invocation-modes`: Defines manual and automatic driver-invocation cases, selectors, catalog integrity, frozen provenance, and invocation-aware reporting.

### Modified Capabilities

None. The directly related system-skill and behavior-testing capabilities remain in completed but unarchived changes, so this change adds independently reviewable follow-up capabilities and explicitly supersedes their explicit-entrypoint and implicit-welcome assumptions.

## Impact

The change affects the packaged system-skill manifest, entrypoint and welcome OpenAI metadata, the admin and agent entrypoint trigger descriptions and workflows, welcome routing behavior, activation documentation, generated or maintained prompt expectations where they describe entrypoint selection, system-skill validation tests, and `skillset/dev/houmao-dev-behavior-testing` catalog, schema, selectors, case pages, reports, and focused structural tests. It does not change pack membership, install projection, static copy-paste compatibility, shared-routine contents, loop operations, runtime authorization, or the explicit initial-root policy of shared routines and loop skills.
