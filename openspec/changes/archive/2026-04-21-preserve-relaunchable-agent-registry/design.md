## Context

The current shared registry contract is live-only: published records live under the shared `live_agents` registry, contain a freshness lease, and are removed when local tmux-backed managed agents stop. That works for live command routing, but it conflates two separate concepts:

- managed-agent identity and runtime ownership, which should remain durable while the runtime home and manifest remain relaunchable
- live process/container liveness, which should disappear when the tmux session or gateway is stopped

Issue #31 exposes the problem. `houmao-mgr agents stop` kills the tmux session and clears the shared registry record, so `houmao-mgr agents relaunch --agent-name ... --chat-session-mode tool_last_or_new` has no target even though the stopped session manifest, runtime home, memory paths, and provider-local chat state remain on disk.

There is already a stopped-session discovery path in cleanup that scans runtime manifests under the effective runtime root. That is useful as a repair fallback, but using it as the primary relaunch index would make relaunch depend on filesystem scans and would keep lifecycle state split across two authorities. The cleaner model is to make the registry lifecycle-aware.

## Goals / Non-Goals

**Goals:**

- Preserve relaunchable managed agents in the registry after `agents stop` by transitioning them to a non-active lifecycle state instead of deleting their registry identity.
- Let `agents relaunch --agent-name/--agent-id` address a stopped relaunchable record directly and revive it without creating a fresh managed-agent identity.
- Keep active-only operations safe by rejecting stopped records for prompt, interrupt, live state, and gateway commands with actionable guidance.
- Separate durable runtime locators from live liveness metadata so stopped records can remain valid without fake leases or fake tmux sessions.
- Make cleanup the explicit destructive lifecycle operation for stopped runtime artifacts and registry records.
- Provide migration behavior for existing v2 live-only records and for stopped sessions that predate lifecycle-aware registry records.

**Non-Goals:**

- Do not make stopped relaunch refresh all latest launch-profile inputs. That broader “reuse existing home while refreshing overlays” workflow belongs to a separate launch/reuse-home change.
- Do not make `agents list` show stopped agents by default unless the operator asks for lifecycle-inclusive output.
- Do not keep stopped records indefinitely as live candidates for gateway or prompt routing.
- Do not require pair/server HTTP authority for local stopped-session relaunch when local manifest authority is available.

## Decisions

### Use a lifecycle-aware managed-agent registry record

Replace the live-only registry record model with a managed-agent record that includes `lifecycle.state` and active-only liveness metadata.

Conceptual shape:

```json
{
  "schema_version": 3,
  "agent_name": "lcr-cc-project-lead",
  "agent_id": "4055420f78cd158ac2a8a271c79498f7",
  "generation_id": "runtime-generation-id",
  "lifecycle": {
    "state": "stopped",
    "relaunchable": true,
    "state_updated_at": "2026-04-20T04:37:30Z",
    "stopped_at": "2026-04-20T04:37:30Z",
    "stop_reason": "operator_stop"
  },
  "identity": {
    "backend": "local_interactive",
    "tool": "claude"
  },
  "runtime": {
    "manifest_path": ".../manifest.json",
    "session_root": ".../sessions/local_interactive/session-id",
    "agent_def_dir": "..."
  },
  "terminal": {
    "kind": "tmux",
    "current_session_name": null,
    "last_session_name": "HOUMAO-lcr-cc-project-lead-1776655306807"
  },
  "liveness": null,
  "gateway": null,
  "mailbox": {}
}
```

Rationale: stopped agents need durable identity and relaunch locators, but must not pretend to have a live tmux session. Nesting active-only liveness avoids the current top-level `lease_expires_at` invariant forcing every registry entry to be live.

Alternative considered: keep the existing live registry and add a second stopped-session registry. That would reduce schema churn, but every selector would need to decide which registry to query and ambiguity would become harder to explain. One lifecycle record per logical managed agent is simpler for users and operators.

### Keep active and relaunchable target resolution separate

Introduce separate resolution helpers for lifecycle-aware lookup:

- active target resolution for prompt, interrupt, state, gateway, and default `agents list`
- relaunch target resolution for `agents relaunch`, which accepts active and stopped relaunchable records
- cleanup target resolution for `agents cleanup`, which accepts stopped records and explicit manifest/session roots

Rationale: most existing commands require a live runtime surface. Allowing all commands to accept stopped records would make failures later and less clear. The selector layer should reject incompatible lifecycle states early.

Alternative considered: let existing target resolution return stopped records everywhere and let each operation fail. That would spread lifecycle checks across many command handlers and make errors inconsistent.

### Make `agents stop` a lifecycle transition

For local tmux-backed records with manifest authority, `agents stop` should:

1. capture manifest path, session root, agent definition root, current tmux session name, gateway state, and mailbox metadata
2. detach/stop live gateway surfaces
3. stop or kill the backend tmux session according to the current stop mode
4. persist the runtime manifest
5. update the registry record to `lifecycle.state = "stopped"`, clear active liveness/gateway endpoints, preserve `last_session_name`, and keep `relaunchable = true` when runtime relaunch authority is present

Rationale: stop should mean inactive, not forgotten. The operator-visible identity should remain addressable until cleanup or retirement.

Alternative considered: preserve the existing live record and let its lease expire. That keeps a stale record temporarily but does not produce a durable relaunch target and makes stopped state indistinguishable from a dead lease.

### Revive stopped sessions through a dedicated runtime path

Do not weaken the current `RuntimeSessionController.relaunch()` invariant that expects a matching live tmux authority. Add a stopped-session revival path that:

1. loads the stopped manifest from the registry runtime pointer
2. reconstructs the controller from the manifest
3. creates a new tmux container or requests one from the backend container setup path
4. mints a fresh registry generation id if needed
5. replaces stale terminal and relaunch authority with the new tmux session name
6. refreshes provider-start launch plan state using the existing relaunch plan rebuild logic
7. starts the provider with the requested relaunch chat-session selector
8. publishes an active lifecycle registry record

Rationale: normal relaunch means “refresh the existing live surface.” Stopped relaunch means “bring the same logical managed agent back to active using its existing runtime home.” The two operations share plan rebuild and provider-start logic, but they have different liveness preconditions.

Alternative considered: clear the persisted tmux session name and call `resume_runtime_session()` so the backend creates a new tmux session as if it were fresh. That can work internally, but it should still be wrapped in an explicit revival operation so manifest authority, registry state, and error messages stay coherent.

### Treat cleanup as destructive lifecycle management

`agents cleanup` should be the path that removes stopped runtime artifacts and then either marks the registry record `retired` or purges it when the operator asks for full deletion.

Recommended default:

- cleanup stopped session artifacts
- update registry record to `retired` with runtime pointers preserved only if they remain useful for audit
- provide `--purge-registry` or equivalent to delete the registry record entirely

Rationale: stopped records are useful operational state; cleanup is the explicit point where the user is saying that relaunch should no longer be expected.

Alternative considered: delete the registry record automatically when cleanup deletes the session root. That is simple, but a retired tombstone gives better auditability and can produce clearer errors for recently retired agent names.

### Preserve migration and recovery paths

The implementation should read existing v2 live records as active lifecycle records when possible. For stopped sessions created before this change, `agents relaunch` may keep the runtime-root scan as a fallback repair path, but the successful recovery should publish a v3 lifecycle record so future operations use the registry.

Rationale: users already have stopped manifests from the old behavior. The new registry model should solve future stops and provide a reasonable bridge for old stopped sessions.

## Risks / Trade-offs

- Registry records may accumulate for stopped agents → Cleanup and retired/purge flows must be clear, and `agents list` should remain active-only by default.
- Existing code assumes every registry record has a fresh live lease → Resolution helpers and model names need a deliberate rename/split so lifecycle records are not accidentally routed as live targets.
- Stopped relaunch may accidentally look like a fresh launch → Responses and docs must say that it reuses the existing runtime home and logical identity, but does not necessarily refresh all latest launch-profile overlay inputs.
- Registry schema migration can break strict validation → Add compatibility loading for v2 records and tests for v2 active records, v3 active records, and v3 stopped records.
- Retired tombstones can create name ambiguity → Exact `agent_id` remains authoritative; friendly-name ambiguity errors must list lifecycle state and candidate ids.

## Migration Plan

1. Add v3 lifecycle-aware registry models and schemas while retaining v2 read compatibility.
2. Rename internal helpers from live-only semantics to managed-agent lifecycle semantics where they load all records, and add explicit active-only wrappers for existing live operations.
3. Update launch publication to write active v3 records.
4. Update stop to transition eligible records to stopped instead of removing them.
5. Add stopped-session revival to relaunch and publish active records after success.
6. Update cleanup to retire or purge stopped records.
7. Keep stopped-manifest scanning as a fallback for pre-change stopped sessions and ambiguous recovery diagnostics.
8. Update tests, docs, and system skill text for stop/relaunch/cleanup behavior.

Rollback strategy: v3 records are local filesystem artifacts. If a rollback is needed, active v3 records can be converted to v2 live records when they have active liveness, and stopped v3 records can be left for the upgraded cleanup/recovery path or addressed by explicit manifest/session-root cleanup.

## Open Questions

- Should cleanup default to `retired` tombstones or direct registry deletion? The design recommends `retired` by default with an explicit purge path.
- Should `agents list --all` include retired records, or should retired records require a separate `--state retired` filter?
- Should stopped records preserve mailbox metadata as durable identity or clear it to avoid stale mailbox routing assumptions? The design recommends preserving mailbox identity metadata but treating notifier/gateway delivery as inactive.
