# Agent Definition Directory

The **agent definition directory** is the source tree Houmao parses before it resolves selectors, builds runtime homes, or launches agents. The canonical layout is now role-scoped presets plus tool-scoped setup/auth bundles.

The default location is `.agentsys/agents/` (override with `AGENTSYS_AGENT_DEF_DIR`). A good template is `tests/fixtures/agents/`.

## Directory Layout

```text
<agent-def-dir>/
├── skills/
│   └── <skill>/SKILL.md
├── roles/
│   └── <role>/
│       ├── system-prompt.md
│       └── presets/
│           └── <tool>/
│               └── <setup>.yaml
├── tools/
│   └── <tool>/
│       ├── adapter.yaml
│       ├── setups/
│       │   └── <setup>/...
│       └── auth/
│           └── <auth>/...
└── compatibility-profiles/
```

## Directory Reference

### `skills/`

Reusable capability packages projected into runtime homes. Each skill directory must contain `SKILL.md`.

### `roles/<role>/system-prompt.md`

The role prompt and behavior policy for one logical agent role.

### `roles/<role>/presets/<tool>/<setup>.yaml`

The canonical declarative launch preset. The file path derives:

- `role` from `<role>`
- `tool` from `<tool>`
- `setup` from `<setup>`

The YAML stores only the data that is not path-derived:

- `skills`
- optional `auth`
- optional `launch`
- optional `mailbox`
- optional `extra`

### `tools/<tool>/adapter.yaml`

The tool adapter defines how Houmao projects setup files, skills, and auth material into the runtime home, plus the tool-specific launch contract.

### `tools/<tool>/setups/<setup>/`

Secret-free checked-in setup bundles for one tool. These replace the older `cli-configs/` terminology.

### `tools/<tool>/auth/<auth>/`

Local-only auth bundles for one tool. These replace the older `api-creds/<tool>/<profile>/` terminology.

### `compatibility-profiles/`

Optional compatibility metadata for specialized CAO or server-facing flows.

## Committed vs. Local-Only

| Directory | Committed | Description |
|---|---|---|
| `skills/` | ✅ Yes | Reusable capability packages |
| `roles/` | ✅ Yes | Role prompts and tracked presets |
| `tools/<tool>/adapter.yaml` | ✅ Yes | Tool projection and launch contract |
| `tools/<tool>/setups/` | ✅ Yes | Secret-free setup bundles |
| `tools/<tool>/auth/` | ❌ Usually no | Local-only auth bundles |
| `compatibility-profiles/` | ✅ Yes | Optional compatibility metadata |

Generated runtime homes and manifests are also disposable and gitignored.

## How The Pieces Connect

1. Houmao parses `skills/`, `roles/`, and `tools/` into a canonical in-process catalog.
2. `houmao-mgr agents launch --agents <role> --provider <provider>` resolves that role to `roles/<role>/presets/<tool>/default.yaml`.
3. The resolved preset selects skills, setup, default auth, and optional launch/mailbox settings.
4. `BrainBuilder` combines the preset with `tools/<tool>/adapter.yaml`, the selected setup bundle, and the effective auth bundle to materialize a runtime home.
5. The runtime pairs the built manifest with `roles/<role>/system-prompt.md` and launches the session on the requested backend.

If you want a small runnable example that uses this exact layout, see [scripts/demo/minimal-agent-launch/tut-agent-launch-minimal.md](../../scripts/demo/minimal-agent-launch/tut-agent-launch-minimal.md).
