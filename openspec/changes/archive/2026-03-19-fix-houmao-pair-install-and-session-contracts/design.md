## Context

The dual shadow-watch HTT run found that the pair boundary is not actually closed for profile installation. The demo had to derive the internal child-CAO home path from the public server base URL and rewrite `HOME` before calling `houmao-srv-ctrl install`. That workaround succeeds operationally, but it contradicts the documented design that `child_cao/` storage is Houmao-managed internal state rather than a caller-facing control surface.

The same HTT run also exposed a weaker contract around session detail. `houmao-srv-ctrl launch` currently reads raw JSON from `GET /sessions/{session_name}` because the typed client models only describe `/terminals/{id}` payloads well enough for current call sites. That left tmux window preservation dependent on ad hoc `dict` access instead of a real compatibility model.

These are system-level pair issues, not demo-local issues. The demo should consume the pair contract, not fix it by learning internal child storage layout or scraping untyped session payloads.

## Goals / Non-Goals

**Goals:**
- Make pair-targeted profile installation route through `houmao-server` instead of through caller-computed child-home paths.
- Keep the supported public boundary as `houmao-server + houmao-srv-ctrl`.
- Add typed session-detail models for the CAO-compatible `GET /sessions/{session_name}` response used by paired Houmao clients.
- Preserve authoritative tmux window identity from session detail into launch registration and runtime artifacts.
- Remove the need for demo or tooling code to know the hidden `child_cao` filesystem layout.

**Non-Goals:**
- Replacing the CAO-backed shallow-cut install behavior with a fully native Houmao profile installer.
- Broadly redesigning every passthrough `houmao-srv-ctrl` command in this change.
- Revisiting the separate state-stability naming work tracked by `add-shadow-watch-state-stability-window`.
- Changing the CAO-compatible public route paths for existing session or terminal endpoints.

## Decisions

### Decision 1: Pair-targeted install goes through a server-owned install surface

**Choice:** Add a Houmao-owned install surface on `houmao-server` that accepts the provider plus agent source/profile input needed for install, resolves the child-managed CAO state internally, executes the install in that server-owned context, and returns explicit success or failure to the caller.

**Rationale:** This restores the intended boundary. Callers should identify the target pair by the public server identity, not by reverse-engineering the filesystem layout under `child_cao/`.

**Alternatives considered:**
- Keep exposing child-home path knowledge to callers.
  Rejected because it makes internal server storage a de facto public contract.
- Re-implement CAO profile installation natively in Houmao immediately.
  Rejected because the shallow cut is still CAO-backed internally and does not need a full native install rewrite to close this boundary.

### Decision 2: `houmao-srv-ctrl install --port` is the additive pair-targeting mechanism

**Choice:** Extend `houmao-srv-ctrl install` with additive `--port` support. When `--port` is present, the CLI verifies the supported pair and routes the install through the target `houmao-server`. When `--port` is absent, local CAO-compatible delegated install behavior may remain unchanged.

**Rationale:** This keeps the CLI CAO-compatible by default while providing a clear pair-owned targeting path for workflows that intentionally operate on a specific running Houmao pair instance.

**Alternatives considered:**
- Make `--port` mandatory for all installs.
  Rejected because it would break CAO-compatible local usage and violate the additive-extension rule.
- Add a separate Houmao-only install command name instead of extending `install`.
  Rejected because the supported operator story is still the CAO-compatible command family under `houmao-srv-ctrl`.

### Decision 3: Session detail gets its own typed model instead of overloading terminal models

**Choice:** Introduce dedicated typed models for session detail and session-terminal summary, and parse `GET /sessions/{session_name}` into those models in the client layer.

**Rationale:** Upstream session detail returns a `session` object plus `terminals` entries whose shape is not identical to `GET /terminals/{id}`. Overloading `CaoTerminal` or leaving the payload untyped keeps pair logic brittle.

**Alternatives considered:**
- Keep using raw `dict[str, object]` payloads at the client boundary.
  Rejected because higher-level pair flows should not depend on ad hoc JSON shape assumptions.
- Force session-detail terminals into the existing `CaoTerminal` model.
  Rejected because the upstream fields are session-summary fields, not full terminal-detail fields.

### Decision 4: Launch registration must preserve tmux window identity from the typed session detail

**Choice:** `houmao-srv-ctrl launch` reads tmux window metadata from the typed session detail response and persists it into registration requests plus runtime artifacts whenever that metadata is available.

**Rationale:** `houmao-server` resolves the tracked tmux pane from registration-seeded identity. Preserving the authoritative tmux window closes the gap between session creation, registration, and tracker admission.

**Alternatives considered:**
- Infer the tmux window from `terminal_id`.
  Rejected because that relationship is not valid and already caused live tracking failures.
- Ignore window identity and let the tracker fall back to the active pane.
  Rejected because it makes first-poll targeting nondeterministic for multi-window sessions.

### Decision 5: This change does not absorb the separate stability-window naming work

**Choice:** Keep the current change focused on pair boundary repair. Document the interaction with the active stability-window change, but do not fold config renaming or stability-surface revisions into this fix.

**Rationale:** The HTT defects that blocked pair operation were install routing and typed session identity. Pulling in the in-progress stability naming work would widen the change unnecessarily and create avoidable overlap with a separate change already in flight.

**Alternatives considered:**
- Combine pair-boundary fixes with the active state-stability-window cleanup.
  Rejected because the two topics are adjacent but not required to unblock the broken pair contract exposed by HTT.

## Risks / Trade-offs

- [Server-owned install remains CAO-backed internally] → Mitigation: keep the contract focused on target selection and ownership boundaries, not on promising native install semantics in v1.
- [Pair-targeted install and local install may diverge subtly] → Mitigation: preserve local delegated behavior when `--port` is absent and add tests that make the routed-vs-local split explicit.
- [Typed session detail may surface upstream shape drift quickly] → Mitigation: pin compatibility verification to the tracked CAO source and keep the new models aligned with that explicit oracle.
- [Existing demo and helper code may still compute child-home paths directly] → Mitigation: switch those flows to the pair-owned install surface in the same implementation change and add regression tests around the new path.

## Migration Plan

1. Add the server-owned install request/response contract and implement the server-side child-context install path.
2. Extend `houmao-srv-ctrl install` with additive `--port` routing to that server-owned install path.
3. Add typed session-detail models and update `houmao-srv-ctrl launch`, query helpers, and related tests to consume them.
4. Remove consumer-side child-home derivation from the dual shadow-watch demo and related helpers.
5. Update pair docs and migration docs to describe `houmao-srv-ctrl install --port` as the supported pair-targeting path.

Rollback remains straightforward: callers can stop using the additive `--port` path and return to local delegated install behavior while implementation work is backed out.

## Open Questions

- Should the server-owned install surface be exposed only as an HTTP extension route, or also as a `houmao-server` CLI wrapper for local operator ergonomics?
- Should `houmao-srv-ctrl init` gain the same pair-targeting pattern now, or should this change intentionally stop at `install` and leave a follow-up audit for other child-state-mutating commands?
