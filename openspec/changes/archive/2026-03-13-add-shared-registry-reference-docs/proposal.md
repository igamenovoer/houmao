## Why

The shared live-agent registry is now defined across multiple completed registry changes and reflected in runtime code and tests, but the official docs still explain it only as one section inside the broader realm-controller page. That makes it hard for new users to build the right mental model and hard for maintainers to find the exact contracts, recovery rules, and runtime integration points without re-reading change artifacts or source.

## What Changes

- Add a dedicated shared-registry reference subtree under `docs/reference/registry/` instead of keeping the full explanation embedded in `docs/reference/realm_controller.md`.
- Split the material into focused pages for overview, operator-facing discovery and cleanup behavior, on-disk and record contracts, ownership and resolution rules, and runtime integration details.
- Explain the shared registry as a locator layer that points to runtime-owned state rather than replacing session manifests, tmux discovery, gateway state, or mailbox state.
- Document the implemented v1 semantics for canonical naming, hashed `agent_key` layout, `generation_id` ownership, lease freshness, malformed-record handling, and cleanup reporting.
- Update reference navigation so top-level reference pages and broader runtime pages link readers into the new registry subtree.
- Keep the broader runtime reference concise by replacing the current long shared-registry section with a summary and links to the dedicated registry pages.

## Capabilities

### New Capabilities
- `registry-reference-docs`: Provide an official reference documentation set for the shared live-agent registry, covering motivation, terminology, contracts, discovery and cleanup workflows, and runtime integration boundaries.

### Modified Capabilities
- None.

## Impact

- Affected docs: `docs/reference/index.md`, `docs/reference/realm_controller.md`, and new pages under `docs/reference/registry/`.
- Affected source material: registry OpenSpec changes, `src/houmao/agents/realm_controller/registry_models.py`, `src/houmao/agents/realm_controller/registry_storage.py`, `src/houmao/agents/realm_controller/runtime.py`, and registry-related unit/integration tests become the main inputs for the new doc set.
- Runtime code impact: none intended; this is a documentation and navigation change that makes the existing shared-registry contract easier to discover and maintain.
