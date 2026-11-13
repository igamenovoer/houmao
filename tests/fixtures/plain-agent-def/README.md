# Plain Agent Definition Fixture Root

This secret-free seed supplies roles, skills, presets, adapters, and setups for explicit direct native construction. It is not a mutable project overlay or a credential store. Use the [test-fixture helper](../../../scripts/agents/test-fixtures/README.md) to select an API case and prepare live agents outside the checkout.

```text
plain-agent-def/
  roles/<role>/system-prompt.md
  skills/<skill>/SKILL.md
  presets/<role>-<tool>-<setup>.yaml
  launch-profiles/<profile>.yaml
  tools/<tool>/adapter.yaml
  tools/<tool>/setups/<setup>/...
  tools/<tool>/auth/.gitignore
```

## Auth Contract

Reusable plain presets have no personal auth default. Select credentials explicitly when copying the tree into a private external run. API cases need no native auth JSON. Native login requires explicit discovery/import into the external XDG auth store. Copy selected credentials before starting a client; never point a writable native home at a reusable store or original vendor file.

## Recommended Workflow

1. Prepare a selected `self-hosted` or `cloud-api` case through `scripts/agents/test-fixtures/fixture.py prepare`, with an explicit model. Kimi also needs a context window.
2. For direct builds, use the prepared external assets with `houmao-mgr internals native-agent brain build --native-agent-root /external/run/assets --preset /external/run/assets/presets/ROLE-TOOL-fixture.yaml`.
3. For managed creation, the helper initializes a project and registers its credential and specialist through existing behavior. `houmao-mgr project agents launch` owns birth.
4. Follow up using `houmao-mgr agents single --agent-id <id> state`, `stop`, or `cleanup session`, with the run's registry/runtime roots selected. The helper's `check` and `stop` commands select these automatically.

Codex's `api-compatible` setup uses Responses and requires explicit routing. Its tracked template contains no endpoint/model account default; brain construction resolves `OPENAI_BASE_URL` from the selected credential and rejects missing or conflicting URLs. `default` remains the native-provider setup. Inspect the [case descriptors](../agent-launch/README.md) for supported protocols and metadata.
