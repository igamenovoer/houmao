## Context

The current pair still exposes CAO compatibility as the default public shape:

- `houmao-server` serves CAO-compatible `/sessions/*` and `/terminals/*` routes at the server root.
- `houmao-srv-ctrl` still exposes CAO verbs at the top level.
- Pair-owned runtime and gateway code still assumes CAO session routes live at the server root.
- Tests codify that shape by comparing root HTTP route inventory and top-level CLI command inventory directly against pinned upstream CAO.

That boundary is no longer aligned with product intent. The supported story is the Houmao pair, not mixed use with raw upstream `cao` or `cao-server`. The user decision for this change is explicit:

- root CAO HTTP routes must be removed, not kept as aliases
- top-level CAO verbs must be removed from `houmao-srv-ctrl`
- the pair must continue to work end to end after the break

This makes the change cross-cutting. It is not only a routing rename. The server, CLI, client helpers, runtime backend, gateway code, tests, and docs all need to agree on the same hard boundary.

## Goals / Non-Goals

**Goals:**
- Make CAO compatibility explicit and non-default on both HTTP and CLI surfaces.
- Move the CAO-compatible HTTP contract to `/cao/*` and remove root CAO route aliases.
- Move CAO-compatible CLI behavior to `houmao-srv-ctrl cao ...` and remove top-level CAO verbs.
- Keep the supported `houmao-server + houmao-srv-ctrl` pair working end to end after the boundary reset.
- Remove internal assumptions that `houmao-server` exposes CAO routes at the root.
- Preserve Houmao-owned root and `/houmao/*` namespaces for Houmao-native behavior.

**Non-Goals:**
- Supporting raw upstream `cao` against `houmao-server`.
- Supporting `houmao-srv-ctrl` against arbitrary external `cao-server` deployments.
- Replacing the child `cao-server` shallow-cut implementation in this change.
- Finalizing the entire long-term Houmao HTTP or CLI information architecture beyond this boundary reset.
- Re-implementing every upstream CAO command natively when a narrower compatibility wrapper is sufficient.

## Decisions

### Decision 1: `houmao-server` exposes CAO compatibility only under `/cao/*`

**Choice:** Move the full CAO-compatible HTTP route family under an explicit `/cao` namespace and remove root CAO aliases.

The resulting public split is:

- Houmao-owned root routes, including `GET /health`
- Houmao-owned native routes under `/houmao/*`
- CAO-compatible routes only under `/cao/*`

Examples:

- `GET /cao/health`
- `GET /cao/sessions`
- `POST /cao/sessions`
- `GET /cao/terminals/{terminal_id}`
- `GET /cao/terminals/{terminal_id}/working-directory`
- `POST /cao/terminals/{terminal_id}/input`

Root CAO routes such as `/sessions/*` and `/terminals/*` are removed instead of being kept as deprecated aliases.

**Rationale:**
- This makes the public server boundary honest: CAO compatibility exists, but it does not own the root.
- It matches the user’s requirement that upstream raw CAO clients do not need to work against the public `houmao-server` surface.
- It frees future Houmao-native root design from permanent CAO route constraints.

**Alternatives considered:**
- Keep root aliases during a transition: rejected because the user explicitly asked for direct removal.
- Move compatibility under `/compat/cao/*` or a versioned tree: rejected as extra complexity without a current need.

### Decision 2: `houmao-srv-ctrl` top level becomes Houmao-owned; CAO compatibility moves under `cao`

**Choice:** Remove CAO verbs from the top level of `houmao-srv-ctrl` and expose CAO compatibility only through a `cao` subcommand namespace.

The intended public split is:

- `houmao-srv-ctrl launch`
- `houmao-srv-ctrl install`
- `houmao-srv-ctrl cao launch`
- `houmao-srv-ctrl cao info`
- `houmao-srv-ctrl cao shutdown`
- `houmao-srv-ctrl cao init`
- `houmao-srv-ctrl cao flow`
- `houmao-srv-ctrl cao mcp-server`
- `houmao-srv-ctrl cao install`

Top-level `launch` and `install` remain, but they are now Houmao-owned pair commands rather than top-level CAO verbs.

**Rationale:**
- This removes the main CLI ambiguity: top level no longer implies long-term CAO parity.
- It still preserves an explicit compatibility path for CAO-shaped workflows.
- It aligns the CLI boundary with the HTTP boundary: `cao` is compatibility, top level is Houmao-owned.

**Alternatives considered:**
- Keep top-level verbs and add `cao` as a second path: rejected because it preserves the same ambiguity.
- Remove CAO compatibility from `houmao-srv-ctrl` entirely: rejected because the pair still needs an explicit compatibility namespace.

### Decision 3: Pair-owned clients stop inheriting the root-CAO assumption

**Choice:** Introduce an explicit CAO-compatibility client seam for `houmao-server` that targets `/cao/*`, and use it everywhere the pair needs CAO-compatible session or terminal behavior.

Concretely:

- `HoumaoServerClient` stops meaning “root CAO client plus extra Houmao helpers”.
- `HoumaoServerClient` becomes a pair client that owns:
  - a Houmao root/native request path for `/health` and `/houmao/*`
  - a CAO-compatibility request path for `/cao/*`
- persisted runtime manifests, gateway attach metadata, and other pair-owned state continue storing `api_base_url` as the public `houmao-server` root authority rather than as a `/cao`-qualified URL
- `houmao_server_rest` runtime control, gateway attach, query helpers, and repo-owned demos stop constructing root-path `CaoRestClient` objects for `houmao-server` and instead use the shared `/cao` compatibility client seam

Implementation may use either:

- composition inside `HoumaoServerClient`, or
- a path-prefix-capable CAO REST client injected where needed

The important contract is the same: pair-owned code must stop assuming that `houmao-server` exposes CAO routes at the root, while persisted pair state continues to identify the public server authority without embedding `/cao`.

**Rationale:**
- This is the main break repair required by the server boundary reset.
- It preserves the existing “one server authority” invariant across manifests and gateway attach contracts.
- It avoids fragile ad hoc string rewrites or caller-specific persisted URLs in multiple modules.
- It keeps raw CAO and pair-owned Houmao transports distinct but reusable.

**Alternatives considered:**
- Hardcode `/cao` string concatenation in each caller: rejected as brittle and repetitive.
- Keep internal callers pointed at the hidden child CAO listener: rejected as the default because it bypasses the public pair boundary and weakens the architectural clarity of `/cao/*`.

### Decision 4: Session-backed `houmao-srv-ctrl cao` commands are pair-aware wrappers, not blind upstream passthrough

**Choice:** Commands that depend on server-backed CAO session state are implemented as repo-owned compatibility wrappers over the public pair boundary rather than as blind `subprocess.run(["cao", ...])` passthrough.

That applies at minimum to:

- `houmao-srv-ctrl cao launch`
- `houmao-srv-ctrl cao info`
- `houmao-srv-ctrl cao shutdown`

These commands preserve CAO-shaped UX where practical, but they operate through the pair’s explicit server boundary and pair-owned follow-up behavior.

For this change, preserving CAO-shaped UX means:

- preserving exit-code behavior
- preserving compatibility-significant stdout and stderr where upstream CAO already exposes machine-readable or script-consumed output
- not promising byte-for-byte parity for every human-oriented line of prose once wrapper-owned messaging is involved

Commands that do not depend on the public server route shape may remain delegated to installed `cao` behavior, including:

- `houmao-srv-ctrl cao init`
- `houmao-srv-ctrl cao flow`
- `houmao-srv-ctrl cao mcp-server`
- `houmao-srv-ctrl cao install` for raw local CAO-compatible install semantics

**Rationale:**
- Blind passthrough no longer works once the public server stops exposing root CAO routes.
- Session-backed pair commands need registration and cleanup behavior that should remain inside the pair contract.
- The explicit `cao` namespace should remain reliable for script-facing compatibility behavior even when wrappers replace blind passthrough.
- Local-only commands do not justify a native rewrite in this change.

**Alternatives considered:**
- Reimplement the full upstream CAO CLI natively: rejected as too large for this boundary reset.
- Keep using installed `cao` against the hidden child listener: rejected as the main strategy because it weakens the explicit `/cao/*` public contract and bypasses pair-owned routing.

### Decision 5: Top-level `launch` and `install` become the canonical pair workflows

**Choice:** Keep top-level `launch` and `install` as pair-owned commands and make them the documented canonical workflow.

For `launch`:

- top-level `houmao-srv-ctrl launch --headless` remains the Houmao-native headless flow
- top-level `houmao-srv-ctrl launch` for TUI-backed sessions remains a pair-owned workflow that creates compatibility sessions through the explicit CAO boundary and still performs Houmao registration and runtime artifact materialization

For `install`:

- top-level `houmao-srv-ctrl install` becomes the pair-owned install path through `houmao-server`
- pair targeting is no longer an additive compatibility branch hanging off a CAO-shaped top-level command

`houmao-srv-ctrl cao install` remains the explicit raw compatibility-oriented install path when an operator intentionally wants CAO-local install behavior.

**Rationale:**
- This gives the pair a clean canonical story after top-level CAO verbs are removed.
- It preserves the existing useful top-level names while letting their semantics become Houmao-owned.
- It avoids forcing users to learn a new top-level verb taxonomy in the same change.

**Alternatives considered:**
- Move all launch and install behavior under `cao`: rejected because it would leave the canonical pair workflow hidden inside the compatibility namespace.
- Invent a new top-level verb set immediately: rejected as a larger CLI redesign than the user asked for.

### Decision 6: Verification and docs move to the explicit boundary

**Choice:** Replace root-compatibility verification with explicit namespaced verification.

That means:

- HTTP parity checks compare `/cao/*` routes against pinned upstream CAO, not root routes
- CLI compatibility checks compare `houmao-srv-ctrl cao ...` against pinned upstream CAO command shapes, not top-level `houmao-srv-ctrl` inventory
- Houmao-owned top-level commands and root routes are tested as pair-owned behavior, not judged by CAO parity

Documentation is updated to describe the boundary in the same terms:

- root and `/houmao/*` are Houmao-owned
- `/cao/*` is CAO compatibility
- top-level `houmao-srv-ctrl` is Houmao-owned
- `houmao-srv-ctrl cao ...` is CAO compatibility

**Rationale:**
- The tests and docs are currently part of the problem because they encode the old root/default compatibility promise.
- Without updating them, implementation will keep drifting back toward the old public shape.

**Alternatives considered:**
- Keep old parity tests temporarily and add parallel namespaced tests: rejected because the user wants a direct contract reset, not a staged migration.

## Risks / Trade-offs

- [Breaking scripts or docs that still call root `/sessions/*` or top-level `houmao-srv-ctrl info`] → Mitigation: update pair docs, migration docs, and command help in the same change; treat the boundary reset as one coherent breaking release.
- [Incomplete internal break repair leaves `houmao_server_rest`, gateway attach, or persisted manifests pointing at removed root CAO routes] → Mitigation: keep persisted `api_base_url` rooted at the public server authority and make one shared `/cao` client seam part of the core implementation rather than follow-up cleanup.
- [Duplicated launch logic between top-level `launch` and `cao launch`] → Mitigation: share common session-backed launch helpers and separate only the user-facing command wiring and messaging.
- [Confusion about `install` semantics between top-level and `cao install`] → Mitigation: document top-level `install` as the canonical pair-owned path and `cao install` as the explicit raw compatibility path.
- [Compatibility wrappers drift in script-facing output or exit semantics] → Mitigation: define regression coverage around exit codes and compatibility-significant stdout/stderr for `houmao-srv-ctrl cao launch/info/shutdown`, without requiring byte-for-byte human-prose parity.
- [Repo-owned demos and demo-backed tests continue calling root-shaped CAO client methods] → Mitigation: include demo and demo-test fallout in the shared client-seam rollout and verification sweep.
- [Future contributors reintroduce root CAO aliases or top-level CAO verbs] → Mitigation: codify the new boundary in delta specs, route inventory tests, and CLI inventory tests.

## Migration Plan

1. Move the server-side CAO route family behind `/cao/*` and delete root CAO route registrations.
2. Update pair-owned server clients, runtime backends, gateway paths, and repo-owned demos to use one shared compatibility client seam while keeping persisted `api_base_url` values rooted at the public server authority.
3. Reshape the `houmao-srv-ctrl` command tree so only the `cao` group exposes CAO compatibility commands.
4. Rework session-backed `cao` commands to use pair-aware implementations over the explicit compatibility boundary while preserving compatibility-significant script-facing behavior.
5. Update top-level `launch` and `install` to be the canonical pair-owned workflows.
6. Replace route and command parity tests, add demo/demo-test fallout coverage, then update reference and migration docs.

Rollback is coarse-grained: revert the entire boundary-reset change. There is no compatibility-alias rollback path inside the same contract because the user explicitly rejected staged root/top-level shims.

## Open Questions

None for proposal readiness. The main boundary choices are decided by the user request, and implementation can proceed against those decisions.
