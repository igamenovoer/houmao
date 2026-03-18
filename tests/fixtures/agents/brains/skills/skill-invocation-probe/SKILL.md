---
name: skill-invocation-probe
description: Reusable narrow probe for verifying that an installed skill can be invoked from trigger wording in a copied dummy-project workdir.
license: MIT
compatibility: Agent Skills format.
metadata:
  author: houmao
  version: "1.0"
---

Write the canonical probe marker for the skill-invocation demo flow.

Use this skill when the user asks for the **workspace probe handshake** for the current workspace. The user prompt does not need to mention this skill's package name or install path.

## Contract

The probe MUST write this exact marker file relative to the current workspace root:

- `.houmao-skill-invocation-demo/markers/workspace-probe.json`

The marker file MUST contain this exact JSON payload:

```json
{
  "schema_version": 1,
  "probe_id": "skill-invocation-demo",
  "marker_kind": "workspace_probe_handshake",
  "status": "ok"
}
```

## Steps

1. Create the parent directory when needed.
2. Write or replace the marker file with the exact payload above.
3. Do not add timestamps, absolute paths, extra keys, or commentary inside the JSON.
4. Reply briefly after the file exists. Prefer naming the relative marker path.

Reference: `references/contract.md`
