## Context

`houmao-srv-ctrl` currently has a narrow native top-level surface: pair launch and install, one `agent-gateway attach` helper, and the explicit `cao` compatibility namespace. `houmao-cli` still carries most runtime-oriented operator actions such as prompt submission, gateway follow-up, mailbox commands, and local build or registry maintenance, even when the supported authority is already the `houmao-server + houmao-srv-ctrl` pair.

The current pair implementation is already close to supporting a broader native CLI. `houmao-server` exposes managed-agent discovery, state, history, transport-neutral request submission, headless turn routes, gateway lifecycle, and gateway mail-notifier state. At the same time, some workflows are still intentionally local or runtime-host specific:

- brain construction is a local artifact-building operation
- shared-registry cleanup is local maintenance
- live gateway prompt and mail routes exist today on the gateway process rather than on `houmao-server`
- TUI stop is available through the compatibility session API, but not yet as one transport-neutral managed-agent route

This change keeps `houmao-cli` available unchanged, but defines a Houmao-owned native command tree on `houmao-srv-ctrl` so the pair can grow into the preferred operator surface without forcing users through CAO vocabulary or direct gateway port access.

## Goals / Non-Goals

**Goals:**

- Make `houmao-srv-ctrl` the preferred pair-native command surface for managed-agent operations.
- Introduce a stable top-level native tree on `houmao-srv-ctrl` centered on `agents`, `brains`, and `admin`.
- Retire the legacy top-level `agent-gateway` helper and consolidate gateway operations under `agents gateway ...`.
- Use `houmao-server` as the primary authority for pair-managed agent discovery, state, prompt, interrupt, stop, gateway, and mail follow-up actions.
- Preserve top-level `launch` and `install` as pair convenience commands.
- Keep `houmao-cli` available and unchanged during this expansion.
- Replace repo-owned `docs/` usage of `houmao-cli` with `houmao-srv-ctrl` wherever the new native pair surface covers the workflow.
- Keep the explicit `cao` namespace intact as the CAO-compatible surface.

**Non-Goals:**

- Retire, rename, or repurpose `houmao-cli` in this change.
- Redesign the `cao` namespace or relax its compatibility obligations.
- Preserve the legacy top-level `agent-gateway` command family as a supported public surface.
- Force local artifact-building or registry-maintenance commands through `houmao-server`.
- Preserve every legacy runtime-control detail as a first-class new native command; in particular, raw `send-keys` remains outside this change's preferred pair-native shape.
- Introduce a brand-new unified launch request that replaces current top-level `launch` behavior in the same step.

## Decisions

### Decision 1: `houmao-srv-ctrl` grows by command families, not by mirroring `houmao-cli` names verbatim

The native top-level shape will be:

- `houmao-srv-ctrl launch ...`
- `houmao-srv-ctrl install ...`
- `houmao-srv-ctrl agents ...`
- `houmao-srv-ctrl brains ...`
- `houmao-srv-ctrl admin ...`
- `houmao-srv-ctrl cao ...`

Within that tree:

- `agents` is the main pair-native operational surface
- `brains` holds local brain-building work
- `admin` holds local maintenance work
- `launch` and `install` stay as ergonomic pair shortcuts rather than being moved immediately under `agents`

Proposed command tree:

```text
houmao-srv-ctrl
  launch ...
  install ...
  agents
    list
    show <agent-ref>
    state <agent-ref>
    history <agent-ref> [--limit N]
    prompt <agent-ref> --prompt "..."
    interrupt <agent-ref>
    stop <agent-ref>
    gateway attach <agent-ref>
    gateway detach <agent-ref>
    gateway status <agent-ref>
    gateway prompt <agent-ref> --prompt "..."
    gateway interrupt <agent-ref>
    mail status <agent-ref>
    mail check <agent-ref>
    mail send <agent-ref> ...
    mail reply <agent-ref> ...
    turn submit <agent-ref> --prompt "..."
    turn status <agent-ref> <turn-id>
    turn events <agent-ref> <turn-id>
    turn stdout <agent-ref> <turn-id>
    turn stderr <agent-ref> <turn-id>
  brains
    build ...
  admin
    cleanup-registry
  cao ...
```

Command-shape conventions:

- agent-scoped native commands use `<agent-ref>` as the first positional identity rather than `--agent` as the normative shape
- prompt-bearing native commands use `--prompt` for explicit text submission, with stdin-friendly behavior handled as an implementation detail rather than as a different public verb
- `agents prompt` is the default documented prompt path, while `agents gateway prompt` is the explicit gateway-mediated path for operators who want gateway admission and queue semantics
- `show` maps to the detail-oriented managed-agent view, while `state` maps to the operational summary view
- `turn` commands stay visible in the native tree even though only managed headless agents accept them; TUI-backed agents fail explicitly at execution time
- the legacy top-level `agent-gateway` helper is retired in this change, and repo-owned invocations move to `agents gateway attach`

Rationale:

- It reflects the actual authority split instead of pretending every action is the same kind of resource.
- It lets `houmao-srv-ctrl` become an umbrella CLI without collapsing native pair commands into CAO vocabulary.
- It avoids a shallow rename-only port of `houmao-cli` that would preserve old wording without clarifying the new pair boundary.

Alternatives considered:

- Reproduce `houmao-cli build-brain`, `start-session`, and related verbs directly on `houmao-srv-ctrl`: rejected because it preserves legacy command shape without making the pair authority clearer.
- Move all native commands immediately under `agents`: rejected because `brains build` and local maintenance are not managed-agent operations.

### Decision 2: `agents` commands are server-authoritative

`houmao-srv-ctrl agents ...` will target managed-agent references and use `houmao-server` as the default authority for:

- list, show, state, and history
- prompt and interrupt
- stop
- gateway attach, detach, and status
- gateway-mediated prompt and interrupt
- mail status, check, send, and reply
- headless turn submission and turn inspection

The CLI should not need to read manifests directly or discover ephemeral gateway ports just to perform ordinary pair-native agent control.
`agents prompt` is the default documented prompt path. `agents gateway prompt` remains available as the explicit gateway-mediated request path when operators want live gateway admission and queue lifecycle rather than the transport-neutral managed-agent request path.

Rationale:

- The server already owns managed-agent identity resolution and most managed-agent read and control routes.
- A server-authoritative CLI gives one coherent operator contract instead of forcing callers to know when to switch from server base URL to gateway endpoint.
- It keeps pair-native commands aligned with the public supported authority.

Alternatives considered:

- Let `srv-ctrl` talk directly to live gateway endpoints for gateway prompt and mail operations: rejected as the primary contract because it leaks implementation topology into the public CLI and complicates remote or proxied usage.
- Keep prompt and stop semantics split between server APIs and local manifest-backed controller recovery: rejected because the new native tree should minimize direct runtime-internals coupling.

### Decision 3: `houmao-server` gets targeted route additions to close remaining authority gaps

The managed-agent API will be extended in three places:

- `POST /houmao/agents/{agent_ref}/stop` becomes transport-neutral for both TUI and headless managed agents, with managed TUI stop implemented through the existing pair-owned CAO session-delete lifecycle rather than a separate tmux-kill mechanism.
- `POST /houmao/agents/{agent_ref}/gateway/requests` proxies live gateway request kinds such as `submit_prompt` and `interrupt`.
- `GET|POST /houmao/agents/{agent_ref}/mail/*` exposes pair-owned managed-agent mail status, check, send, and reply routes so callers do not have to address gateway ports directly.

In v1, the server-owned managed-agent mail routes proxy an attached eligible live gateway and fail explicitly when no eligible live gateway is attached. They do not add a direct runtime-backed fallback in the same change.
These operational `mail/*` routes coexist with the existing `gateway/mail-notifier` CRUD routes: notifier routes configure background notification behavior, while `mail/*` handles foreground mailbox status and actions.
The new server routes reuse the existing HTTP status plus `detail` error pattern rather than introducing a new structured error envelope.

Rationale:

- These additions let the new `agents` tree stay coherent and server-facing.
- They reuse existing managed-agent alias resolution rather than forcing callers to pivot into raw session or gateway identities.
- They keep transport-specific operational detail behind the server boundary.

Alternatives considered:

- Keep TUI stop as a CLI-side composition of `GET /houmao/agents/{ref}` plus `DELETE /cao/sessions/{session}`: rejected as the long-term public contract because `agents stop` should not require CLI-side transport branching.
- Add no server routes and let `srv-ctrl` proxy directly to the live gateway: rejected because it creates two public authorities for one native command family.

### Decision 4: `brains build` and `admin cleanup-registry` stay local to `houmao-srv-ctrl`

`houmao-srv-ctrl brains build` will wrap the existing local brain builder. `houmao-srv-ctrl admin cleanup-registry` will wrap the existing local stale-registry cleanup helper.

These commands are intentionally not server APIs.
For `brains build`, v1 command arguments should align with the lower-level builder inputs that map directly to `BuildRequest` and `brain_builder.py` semantics rather than promising a verbatim mirror of every legacy `houmao-cli build-brain` convenience flag.

Rationale:

- Brain construction is local artifact materialization over the caller's agent-definition directory, config profiles, and credentials.
- Shared-registry cleanup is local host maintenance tied to local runtime-owned paths.
- Forcing these operations through `houmao-server` would blur the supported pair authority instead of clarifying it.

Alternatives considered:

- Add builder and cleanup HTTP routes to `houmao-server`: rejected because those actions are host-local and not natural public server responsibilities.

### Decision 5: The new native tree keeps `houmao-cli` and core pair shortcuts, but retires legacy `agent-gateway`

This change does not retire `houmao-cli`. Existing `houmao-srv-ctrl` top-level `launch`, `install`, and `cao` commands remain. The legacy top-level `agent-gateway` command family is retired in this change, and pair-owned gateway operations move to `agents gateway ...`.

Rationale:

- The user explicitly wants `houmao-cli` kept available.
- `agent-gateway` is already a narrow helper that does not match the new command-family layout.
- Retiring it now prevents the repo from carrying two public gateway command shapes for the same pair-owned operation.
- Repo-owned docs, tests, and examples should converge on one command spelling during the same change.

Alternatives considered:

- Make `houmao-cli` a forwarding shim immediately: rejected because this change is about command design and pair-native authority, not binary retirement.
- Keep `agent-gateway attach` as a compatibility alias: rejected because this would preserve two public gateway entrypoints for the same operation and prolong repo-owned usage drift.

### Decision 6: Repo-owned docs migrate to `houmao-srv-ctrl` wherever the new native surface applies

Repo-owned documentation under `docs/` should prefer `houmao-srv-ctrl` for pair-managed workflows whenever the new native command tree covers the operation.

This means:

- replace `houmao-cli` examples for overlapping pair-native flows such as prompt submission, gateway attach or follow-up, mailbox follow-up, local brain build, and registry cleanup
- keep `houmao-cli` examples only where the workflow is not yet covered by `houmao-srv-ctrl` or where the workflow is intentionally runtime-local rather than pair-managed
- update migration and reference docs so the documented default for supported pair workflows becomes `houmao-srv-ctrl`
- document the managed-agent history retention model so operators can tell what accumulates only in memory versus what is persisted on disk for long-running agents; at minimum this includes the bounded in-memory recent-transition history for TUI-managed agents and the persisted turn-record storage for managed headless agents

Rationale:

- The user explicitly wants the doc set to shift to `houmao-srv-ctrl` whenever possible.
- Long-running operators need explicit guidance on memory-versus-disk accumulation when using `agents history`, not just command spelling.
- Leaving `houmao-cli` as the dominant example surface in `docs/` would undermine the command-tree consolidation this change is trying to achieve.
- Keeping `houmao-cli` documented only for uncovered workflows preserves compatibility without advertising the old runtime CLI as the default for pair-managed operations.

Alternatives considered:

- Leave existing `docs/` examples unchanged and only add new `houmao-srv-ctrl` docs: rejected because the repo would continue presenting two competing defaults for the same workflows.
- Rewrite every `houmao-cli` mention in `docs/` unconditionally: rejected because some workflows still legitimately belong to `houmao-cli` until the new native surface actually covers them.

## Risks / Trade-offs

- [Server API grows beyond the current managed-agent read surface] → Keep additions tightly scoped to native pair operations that the CLI already needs, and reuse existing request and mail models where possible.
- [Users may be confused by overlapping `houmao-cli` and `houmao-srv-ctrl` workflows] → Position `houmao-srv-ctrl` as the preferred pair-native surface in docs while explicitly saying that `houmao-cli` remains available during the transition.
- [Docs migration may overreach and remove valid `houmao-cli` examples] → Replace `houmao-cli` only where the new native pair surface covers the workflow; keep it where the workflow remains uncovered or intentionally runtime-local.
- [Operators may misunderstand long-running history footprint] → Document the history retention model in `docs/`, including the difference between bounded in-memory TUI history and persisted headless turn records, so `agents history` does not look uniformly durable or uniformly ephemeral.
- [Gateway and mail proxy routes may still depend on live gateway health] → Return explicit availability or admission failures from the server-owned routes and avoid pretending that work was accepted when no live control path exists.
- [TUI and headless stop semantics may drift] → Normalize both behind one managed-agent stop contract and return one transport-neutral response shape.
- [Native tree becomes too large or inconsistent] → Keep the top-level split by authority: `agents` for server-managed agent operations, `brains` for local build, `admin` for local maintenance, `cao` for compatibility.

## Migration Plan

1. Extend `houmao-server` models, client helpers, routes, and service logic for transport-neutral stop plus server-owned gateway-request and mail routes.
2. Add `houmao-srv-ctrl agents ...` commands over those server routes, with `show` mapped to the managed-agent detail view and `agents prompt` documented as the default prompt path.
3. Implement the `agents` command family as a `src/houmao/srv_ctrl/commands/agents/` sub-package with per-subgroup modules rather than one oversized module.
4. Retire the top-level `agent-gateway` command family and migrate repo-owned gateway attach usage to `houmao-srv-ctrl agents gateway attach`.
5. Add `houmao-srv-ctrl brains build` and `houmao-srv-ctrl admin cleanup-registry` as local command families over existing helpers, using a `brains build` argument surface aligned with `BuildRequest`.
6. Keep `houmao-cli` unchanged, but audit `docs/` and replace `houmao-cli` usage with `houmao-srv-ctrl` wherever the new native pair surface covers the workflow.
7. Update `docs/` to explain managed-agent history retention and storage location, including what remains only in memory for TUI-managed agents versus what is persisted on disk for managed headless agents.

## Open Questions

No open questions remain for this change after the recorded review decisions.
