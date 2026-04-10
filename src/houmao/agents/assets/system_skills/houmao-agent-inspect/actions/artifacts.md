# Inspect Runtime Artifacts

Use this action when the user wants the durable runtime file layout or the stable artifact paths behind one managed session.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target is still missing, ask the user in Markdown before proceeding.
4. Run `agents state` or `GET /houmao/agents/{agent_ref}/state` first to recover stable identity fields such as `manifest_path` and `session_root`.
5. Use `GET /houmao/agents/{agent_ref}/state/detail` when the task also needs transport-specific detail before inspecting files.
6. Treat `manifest.json` as the durable session record and `session_root` as the stable runtime envelope.
7. For gateway-capable sessions, inspect `gateway/state.json` for durable last-known gateway status and `gateway/logs/gateway.log` or `gateway/events.jsonl` only as log-style evidence.
8. For headless sessions, inspect the turn-artifact files under the session root when the user needs raw provider output beyond `agents turn stdout|stderr`.
9. Report which artifacts are stable operator-facing state versus implementation detail.

## Stable Artifact Targets

- `<session-root>/manifest.json`
- `<session-root>/gateway/state.json`
- `<session-root>/gateway/logs/gateway.log`
- `<session-root>/gateway/events.jsonl`
- headless turn artifacts under `<session-root>/<manifest-stem>.turn-artifacts/<turn-id>/`

Current implementation-detail artifacts that may still be useful for debugging:

- `<session-root>/gateway/run/current-instance.json`
- `<session-root>/gateway/run/gateway.pid`
- raw queue storage such as `<session-root>/gateway/queue.sqlite`

## Guardrails

- Do not treat implementation-detail files as the primary compatibility contract when `manifest.json`, `session_root`, or `gateway/state.json` already answer the question.
- Do not describe `gateway/logs/gateway.log` as durable gateway state.
- Do not mutate runtime artifacts in place as part of inspection.
- Do not skip the managed-agent identity surfaces before filesystem inspection when the target session root is not already known.
