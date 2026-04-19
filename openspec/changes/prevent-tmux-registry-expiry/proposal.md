## Why

Tmux-backed managed agents can remain live and usable after the shared-registry lease on their `record.json` expires. When that happens, `houmao-mgr agents list` and other registry-backed local resolution flows lose track of still-running sessions even though tmux remains the effective runtime authority.

This makes long-lived local managed agents disappear from discovery for reasons unrelated to their actual lifecycle. The change is needed now because issue #20 shows the current 24-hour lease boundary is too short for real operator workflows and there is no resident heartbeat path keeping ordinary tmux-backed sessions refreshed.

## What Changes

- Change shared-registry publication semantics for tmux-backed live agents so their discoverability does not expire independently of the owning tmux session lifecycle.
- Publish tmux-backed records with a dedicated long finite sentinel lease window instead of the ordinary 24-hour live-agent lease or the existing 30-day joined-session sentinel.
- Apply the tmux-backed sentinel to all currently supported tmux-backed registry records, including joined tmux sessions.
- Keep ordinary registry storage and local managed-agent list/selector discovery lease-based; do not add eager tmux probes to those lookup paths.
- Preserve passive server discovery as an existing probe-backed index that still requires both lease freshness and live tmux presence.
- Keep explicit record removal on clean stop/teardown and keep stale cleanup responsible for removing dead tmux-backed records when the session is gone.
- Do not introduce new non-tmux registry publication behavior; current non-tmux/no-publish paths remain unchanged.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `agent-discovery-registry`: tmux-backed live-agent records remain discoverable past the former 24-hour expiry boundary and rely on teardown or cleanup for stale removal.

## Impact

- Affected code: shared-registry record construction and TTL selection in `src/houmao/agents/realm_controller/runtime.py`, registry lease constants and helpers in `src/houmao/agents/realm_controller/registry_storage.py`, and local discovery/listing behavior validated through existing registry-backed command paths.
- Affected tests: registry storage tests, passive discovery tests, and any managed-agent list or selector tests that assume tmux-backed records age out after 24 hours.
- Operational impact: dead tmux-backed records may remain visible longer in ordinary local registry-backed discovery until teardown or cleanup runs, but still-live tmux-backed agents will no longer disappear from local discovery simply because their lease aged out.
