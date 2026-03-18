# Skill Invocation Probe Contract

This reusable fixture exists for one narrow question:

> Can the installed skill be invoked from ordinary trigger wording without naming the skill package or install path?

## Trigger Wording

The stable trigger phrase is:

- `workspace probe handshake`

Future demos or tests may wrap that phrase in a natural sentence, but they should keep the phrase itself stable so the fixture contract stays reusable across tool lanes.

## Marker Contract

Expected marker path relative to the launched workdir:

- `.houmao-skill-invocation-demo/markers/workspace-probe.json`

Expected marker payload:

```json
{
  "schema_version": 1,
  "probe_id": "skill-invocation-demo",
  "marker_kind": "workspace_probe_handshake",
  "status": "ok"
}
```

The marker payload is intentionally minimal and deterministic so demo helpers and tests can verify invocation through a workdir-local side effect instead of transcript text.
