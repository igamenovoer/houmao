# Agent Definition Directory

The **agent definition directory** is the source tree Houmao parses before it resolves selectors, builds runtime homes, or launches agents. The canonical layout is role-scoped presets plus tool-scoped setup/auth bundles.

For repo-local workflows, the supported path is `houmao-mgr project init`, which creates:

```text
<repo>/
└── .houmao/
    ├── .gitignore
    ├── houmao-config.toml
    └── agents/
```

The whole `.houmao/` overlay is local-only by default because `.houmao/.gitignore` contains `*`.

Commands that need an agent-definition root resolve it with this precedence:

1. explicit CLI `--agent-def-dir`
2. `AGENTSYS_AGENT_DEF_DIR`
3. nearest ancestor `.houmao/houmao-config.toml`
4. legacy `<pwd>/.agentsys/agents`

## Directory Layout

```text
<repo>/
└── .houmao/
    ├── houmao-config.toml
    ├── agents/
    │   ├── skills/
    │   │   └── <skill>/SKILL.md
    │   ├── roles/
    │   │   └── <role>/
    │   │       ├── system-prompt.md
    │   │       └── presets/
    │   │           └── <tool>/
    │   │               └── <setup>.yaml
    │   ├── tools/
    │   │   └── <tool>/
    │   │       ├── adapter.yaml
    │   │       ├── setups/
    │   │       │   └── <setup>/...
    │   │       └── auth/
    │   │           └── <auth>/...
    │   └── compatibility-profiles/
    └── mailbox/                      # optional, created only when mailbox workflows are enabled
```

`houmao-mgr project init` seeds `tools/` for supported tools. You author `skills/` and `roles/` locally inside the overlay.

The repo-local project surface is intentionally split into three views:

- `houmao-mgr project agents ...` for low-level filesystem-oriented source management
- `houmao-mgr project easy ...` for higher-level specialist and instance authoring
- `houmao-mgr project mailbox ...` for project-scoped mailbox-root operations against `.houmao/mailbox`

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

Secret-free checked-in setup bundles for one tool. `houmao-mgr project init` seeds the current packaged setup bundles for supported tools here.

### `tools/<tool>/auth/<auth>/`

Local-only auth bundles for one tool. `houmao-mgr project agents tools <tool> auth add ...` writes these bundles for you under `.houmao/agents/tools/<tool>/auth/<name>/`.

### `compatibility-profiles/`

Optional compatibility metadata for specialized CAO or server-facing flows.

### `.houmao/mailbox/`

Optional project-local mailbox root. `houmao-mgr project init` does not create it by default. Enable it only when you want repo-scoped mailbox registrations and direct mailbox reads through `houmao-mgr project mailbox ...`.

## Committed vs. Local-Only

| Directory | Committed | Description |
|---|---|---|
| `.houmao/agents/skills/` | ❌ No | Repo-local reusable capability packages |
| `.houmao/agents/roles/` | ❌ No | Repo-local role prompts and presets |
| `.houmao/agents/tools/<tool>/adapter.yaml` | ❌ No | Local copy of the tool projection and launch contract |
| `.houmao/agents/tools/<tool>/setups/` | ❌ No | Local copy of secret-free setup bundles |
| `.houmao/agents/tools/<tool>/auth/` | ❌ No | Local-only auth bundles |
| `.houmao/agents/compatibility-profiles/` | ❌ No | Optional local compatibility metadata |
| `.houmao/mailbox/` | ❌ No | Optional project-local mailbox root |

Generated runtime homes and manifests are also disposable. If the runtime later creates `.houmao/jobs/` under the repo root, that scratch subtree is still runtime-local scratch, not tracked project source.

## How The Pieces Connect

1. Houmao parses `skills/`, `roles/`, and `tools/` into a canonical in-process catalog.
2. `houmao-mgr agents launch --agents <role> --provider <provider>` resolves that role to `roles/<role>/presets/<tool>/default.yaml`.
3. The resolved preset selects skills, setup, default auth, and optional launch/mailbox settings.
4. `BrainBuilder` combines the preset with `tools/<tool>/adapter.yaml`, the selected setup bundle, and the effective auth bundle to materialize a runtime home.
5. The runtime pairs the built manifest with `roles/<role>/system-prompt.md` and launches the session on the requested backend.

## Authoring Paths

The same canonical `.houmao/agents/` tree can be authored through two different UX layers:

- `project easy specialist create ...` is the primary project-local authoring path when you want one reusable specialist compiled into the canonical tree.
- `project agents ...` is the low-level maintenance surface when you want to inspect or mutate roles, presets, setups, or auth bundles directly.
