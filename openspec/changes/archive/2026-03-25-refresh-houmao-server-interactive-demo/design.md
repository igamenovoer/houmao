## Context

The `houmao-server-interactive-full-pipeline-demo` pack now sits between two eras of the repository. The active implementation already starts a demo-owned `houmao-server`, launches the session through the server's native headless launch API, persists the `houmao_server` manifest bridge, and performs all follow-up operations through direct HTTP routes. However, several repo-owned artifacts still describe the older `houmao-mgr cao launch --headless` path.

The pack also ships a copied `agents/` directory that has drifted from `tests/fixtures/agents/`, even though the main spec already requires a tracked symlink to the fixture tree. In addition, the demo still exposes a demo-owned create-timeout override, but the current startup code does not pass that timeout into `HoumaoServerClient`, so the documented startup budget is not fully honored.

This is a cross-cutting refresh across the demo pack layout, operator-facing documentation/help text, the Python startup path, and the OpenSpec contract for the existing `houmao-server-interactive-full-pipeline-demo` capability.

## Goals / Non-Goals

**Goals:**

- Restore a single source of truth for demo agent definitions by replacing the copied `agents/` tree with the tracked symlink to `tests/fixtures/agents/`.
- Make the README, shell wrappers, Python CLI help, and spec language describe the actual startup flow that exists today.
- Preserve the current server-backed startup and follow-up model for the demo, including the persisted `houmao_server` bridge and managed-agent HTTP routes.
- Ensure the existing demo-owned create-timeout override is actually applied to the native launch client so the documented startup budget remains effective.

**Non-Goals:**

- Migrating this demo to local `houmao-mgr agents launch`.
- Redesigning `houmao-server` APIs, managed-agent route contracts, or the manifest bridge schema.
- Changing the fixture-tree structure under `tests/fixtures/agents/`.
- Renaming the existing demo environment variables just because their historical `compat` naming is no longer perfect.

## Decisions

### D1: Replace the copied demo `agents/` tree with a tracked symlink to `tests/fixtures/agents/`

**Decision**: The checked-in `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents` directory will be removed and replaced by a repository-tracked relative symlink to `tests/fixtures/agents/`.

**Why**: The current copy has already drifted from the fixture source. A symlink restores the contract already described by the main spec, removes sync work, and guarantees the demo resolves the same native selector inputs as the maintained fixture tree.

**Alternatives considered**:

- Keep a minimal copied demo-local tree: rejected because it has already drifted and would keep reintroducing maintenance overhead.
- Add a sync script that regenerates the copy: rejected because it adds another workflow to remember and still leaves room for stale checked-in content.

### D2: Keep the demo on the current server-backed launch model

**Decision**: The demo will continue to start its own `houmao-server`, launch through the server's native headless launch API, persist the `houmao_server` bridge from the returned manifest, and use direct `houmao-server` HTTP routes for inspect/prompt/interrupt/stop.

**Why**: This is the model the current Python implementation already uses, and it is what gives the demo its stable `api_base_url`, `agent_ref`, and `terminal_id` contract. Switching again to local `houmao-mgr agents launch` would be a second architectural change, not a refresh.

**Alternatives considered**:

- Migrate now to `houmao-mgr agents launch`: rejected for this change because it would alter the demo's control model and would need a separate design for how the demo regains server-backed identifiers and managed-agent routes.
- Reintroduce `houmao-mgr cao launch` language for backward familiarity: rejected because that CLI surface has already been retired.

### D3: Refresh wording to describe behavior, not legacy command names

**Decision**: Operator-facing documentation and spec text will describe the startup flow in implementation-accurate terms such as "native headless launch API" and "demo-owned `houmao-server`", rather than naming retired `houmao-mgr cao` commands.

**Why**: The demo's contract is the behavior and persisted state, not which legacy wrapper command once triggered it. Describing the actual mechanism keeps the docs aligned even as the manager CLI evolves.

**Alternatives considered**:

- Mention both old and new wording: rejected because it would preserve ambiguity and invite readers to try retired commands.
- Rewrite everything around `houmao-mgr server start` / `agents launch`: rejected because those are adjacent CLI surfaces, not the demo's internal startup mechanism today.

### D4: Wire the existing create-timeout override into `HoumaoServerClient`

**Decision**: The startup path will instantiate `HoumaoServerClient` with `create_timeout_seconds=env.compat_create_timeout_seconds` for the native headless launch flow.

**Why**: The demo already documents and exposes a create-timeout override intended to make slow startup reliable. Keeping the option while not applying it is misleading. Wiring it through is smaller and safer than deleting the option and revising every related expectation.

**Alternatives considered**:

- Remove the create-timeout option from the demo: rejected because the demo still benefits from a longer launch budget in slow environments, and the repo already treats that budget as part of the demo contract.
- Leave the option in place but only fix documentation: rejected because it would preserve a behavior/documentation mismatch.

## Risks / Trade-offs

- **[Risk] Fixture changes now affect the demo immediately** → Mitigation: accept the fixture tree as the canonical source of truth for this demo and validate demo startup when fixture recipes or roles change.
- **[Risk] Symlink behavior can be awkward on some filesystems or tooling** → Mitigation: use a normal repository-tracked relative symlink and verify it in tests or demo validation scripts that inspect the pack layout.
- **[Risk] Some stale wording may remain outside the core demo files** → Mitigation: update the main demo README, shell wrapper help, Python help strings, and OpenSpec delta in the same change so the highest-signal entry points stay aligned.
- **[Risk] The create-timeout budget may still be misunderstood as a server startup timeout** → Mitigation: document it specifically as the native launch request budget and keep the server startup timeout documented separately.

## Migration Plan

1. Replace the copied demo `agents/` directory with the tracked relative symlink.
2. Update the demo README and shell wrapper help to describe the current startup flow and the shared fixture source.
3. Update the Python demo help strings and startup code so the create-timeout option is accurately described and actually applied.
4. Update the existing OpenSpec capability with a delta spec that reflects the refreshed startup contract.
5. Validate the demo layout and startup-related behavior with targeted tests or demo verification commands.

Rollback is straightforward during development: restore the copied `agents/` tree and revert the wording/code changes if the symlinked fixture source proves unworkable.

## Open Questions

- Should a later cleanup rename `DEMO_COMPAT_CREATE_TIMEOUT_SECONDS` and related flags to remove the historical `compat` wording, or is preserving the current flag surface preferable for now? This change defers that rename and keeps the current flag names.
