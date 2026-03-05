## Context

The brain launch runtime currently persists a session manifest JSON and requires callers to provide the manifest path for control operations (prompt/stop). For CAO-backed sessions, the runtime also creates a tmux session, but the session name is generated from role + timestamp/uuid, which is not ergonomic for humans operating multiple concurrent agents.

We want a human-friendly "agent identity" handle for tmux-backed agents:
- easy to type,
- discoverable via `tmux ls`,
- and able to resolve to the correct session manifest without assuming all agents share one runtime root directory.

Constraint: name-based addressing is explicitly tmux-oriented (CAO/tmux-backed sessions). Non-tmux backends (headless, codex app-server) can continue to be addressed by manifest path until a separate capability adds a different resolution mechanism.

## Goals / Non-Goals

**Goals:**
- Replace `--session-manifest <path>` with `--agent-identity <name|manifest-path>` for session control commands.
- Define a canonical tmux session naming scheme for agent-system sessions using the `AGENTSYS-` namespace.
- Reserve `AGENTSYS` (exact string) so it cannot be used as an agent name.
- Reject user-provided agent names whose *name portion* contains `AGENTSYS` as a standalone token (token boundaries are non-alphanumeric or string boundaries), to avoid confusing nested namespacing.
- For tmux-backed sessions, store the session manifest path in the tmux session environment as `AGENTSYS_MANIFEST_PATH` so a name can be resolved to a manifest without runtime-root scanning.
- Preserve the existing "manifest is the source of truth" behavior for CAO control operations (CAO base URL + terminal ID are taken from the manifest once loaded).

**Non-Goals:**
- Providing name-based addressing for non-tmux backends in this change.
- Introducing a separate global registry directory for name -> manifest mapping.
- Changing the session manifest schema version (we rely on existing fields and tmux env for the mapping).

## Decisions

### 1) Use a single `--agent-identity` CLI argument for both addressing forms

**Decision:** Replace `--session-manifest` with `--agent-identity`, where the value can be either:
- a manifest path (explicit, stable), or
- a short agent name (human handle for tmux-backed sessions).

**Rationale:** One flag reduces user confusion and keeps the UX consistent across prompt/stop operations.

**Alternatives considered:**
- `--agent-name` + `--session-manifest` dual inputs: rejected because it keeps the manifest-path-first UX and increases surface area.
- Separate `--agent-session` vs `--agent-manifest`: rejected as redundant.

### 2) Treat `AGENTSYS-...` as the canonical tmux namespace; reserve `AGENTSYS`

**Decision:** Canonicalize agent names into tmux session names:
- The namespace prefix is exactly `AGENTSYS-` (case-sensitive).
- If the user provides `NAME` that does not start with exact `AGENTSYS-`, the system targets `AGENTSYS-NAME` (no case conversion).
- If the user provides `AGENTSYS-NAME`, use it as-is (no case conversion).
- Reject the exact string `AGENTSYS` as an invalid explicit agent name.
- Validate the *name portion* (after stripping an optional exact `AGENTSYS-` prefix) so it MUST NOT contain `AGENTSYS` as a standalone token, where token boundaries are defined by `[^0-9A-Za-z]` and string boundaries. Substring occurrences inside a larger alphanumeric run (for example `MYAGENTSYS`, `AGENTSYSFOO`) are allowed.
- Validate the *name portion* character set to a conservative tmux+filesystem-safe subset: ASCII letters/digits plus `_` and `-`, with a leading letter/digit requirement. The system SHALL not enforce an additional length cap beyond tmux constraints.
- If the user-provided identity does not start with exact `AGENTSYS-` but contains the substring `AGENTSYS` in a case-insensitive way, emit a warning that the prefix was not exact and that the identity will be treated as missing the namespace prefix.

**Rationale:** Prefixing makes agent-system sessions easy to find and avoids collisions with unrelated tmux sessions. Reserving `AGENTSYS` avoids ambiguous “namespace root” identities.

**Alternatives considered:**
- No prefix: rejected because it increases collisions and reduces discoverability.
- Using a runtime-root registry instead of tmux naming: rejected per constraint (agents may not share one runtime root).

### 3) Embed manifest path in tmux env var `AGENTSYS_MANIFEST_PATH`

**Decision:** For tmux-backed session start, write `AGENTSYS_MANIFEST_PATH=<absolute manifest path>` into the tmux session environment.

**Rationale:** This creates a local, per-tmux-session pointer that survives runtime-root changes and avoids scanning the filesystem for manifests.

**Implementation note:** The runtime needs the manifest path before (or during) tmux session creation. The preferred approach is to allocate `session_id`/`manifest_path` early in `start_session`, then pass the manifest path down to the CAO/tmux launch code so it can set `AGENTSYS_MANIFEST_PATH` immediately after creating the tmux session.

**Alternatives considered:**
- Write a `runtime_root/identities/<name>.json` pointer file: rejected because it assumes a shared runtime root.
- Encode the manifest path into the tmux session name: rejected due to length, readability, and exposure of filesystem paths in `tmux ls`.

### 4) Resolve name-based identities via tmux environment at prompt/stop time

**Decision:** When a caller passes `--agent-identity <name>` (not a path), the runtime:
1. canonicalizes to a tmux session name (for example `AGENTSYS-gpu`),
2. reads `AGENTSYS_MANIFEST_PATH` from that tmux session,
3. loads the session manifest JSON from that path,
4. performs prompt/stop using the manifest's persisted backend fields.

**Rationale:** This keeps the session manifest as the single persisted control contract, while providing an ergonomic name handle.

**Alternatives considered:**
- Use `tmux list-sessions` + parse pane history to infer identity: rejected (brittle, slow, not explicit).

## Risks / Trade-offs

- [Name conflicts with existing tmux sessions] -> Mitigation: require uniqueness for explicit user-provided names; auto-generated names include a conflict-avoiding suffix.
- [Old tmux sessions do not have `AGENTSYS_MANIFEST_PATH`] -> Mitigation: fail with an actionable error and suggest using an explicit manifest path or restarting the agent.
- [tmux not available / not on PATH] -> Mitigation: name-based addressing is only supported for tmux-backed backends; failures are explicit.
- [Manifest path points to a deleted file] -> Mitigation: fail fast with a clear "manifest missing" error; the tmux session is treated as stale.

## Migration Plan

1. Add `--agent-identity` to prompt/stop CLIs and deprecate/remove `--session-manifest`.
2. Add agent identity normalization logic (reserved keyword + `AGENTSYS-` prefix rules).
3. Update CAO/tmux session start to accept a chosen session name and to set `AGENTSYS_MANIFEST_PATH`.
4. Update prompt/stop resolution:
   - manifest-path identity: current behavior,
   - name identity: resolve via tmux env pointer then resume via manifest.
5. Update demo scripts and docs to use `--agent-identity`.
6. Add unit tests for:
   - identity parsing (path vs name),
   - reserved keyword handling,
   - tmux env pointer read/write behavior (with tmux shim/mocks as needed).

Rollback strategy:
- Re-introduce `--session-manifest` as a temporary compatibility alias if needed, but prefer a clean break since this is a CLI ergonomics change.

## Open Questions

- Should non-tmux backends support name-based `--agent-identity` in a future change (this change is tmux-only for name-based resolution)?
