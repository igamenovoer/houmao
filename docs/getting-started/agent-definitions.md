# Agent Definition Directory

The **agent definition directory** is the source tree Houmao parses before it resolves selectors, builds runtime homes, or launches agents. The canonical layout is role-scoped presets plus tool-scoped setup/auth bundles.

For repo-local workflows, the supported path is `houmao-mgr project init`, which creates:

```text
<repo>/
└── .houmao/
    ├── .gitignore
    ├── houmao-config.toml
    ├── catalog.sqlite
    ├── content/
    └── agents/   # compatibility projection, materialized on demand
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
    ├── catalog.sqlite
    ├── content/
    │   ├── prompts/
    │   ├── auth/
    │   ├── skills/
    │   └── setups/
    ├── agents/                       # compatibility projection, materialized on demand
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
    │   └── compatibility-profiles/   # optional, created only when explicitly enabled
    └── mailbox/                      # optional, created only when mailbox workflows are enabled
```

`houmao-mgr project init` seeds the managed content roots and the SQLite catalog. It does not create `.houmao/agents/`, `compatibility-profiles/`, `.houmao/mailbox/`, or `.houmao/easy/` unless you opt into workflows that need those paths explicitly.

The repo-local project surface is intentionally split into three views:

- `houmao-mgr project agents ...` for low-level filesystem-oriented source management
- `houmao-mgr project easy ...` for higher-level specialist and instance authoring
- `houmao-mgr project mailbox ...` for project-scoped mailbox-root operations against `.houmao/mailbox`

## Directory Reference

### `catalog.sqlite`

The canonical semantic store for project-local specialists, roles, presets, setup profiles, skill packages, auth profiles, and managed content references. Advanced operators can inspect stable read views such as `v_specialists`, `v_presets`, and `v_content_refs` directly with SQLite tooling.

### `content/`

Managed file-backed payload storage. Large text blobs and tree-shaped payloads such as prompt files, auth bundles, skill packages, and setup bundles live here even though their semantic relationships are owned by `catalog.sqlite`.

### `skills/`

Reusable capability packages projected into runtime homes. Under `.houmao/agents/` this is now a compatibility projection fed from `catalog.sqlite` and `.houmao/content/`.

### `roles/<role>/system-prompt.md`

The role prompt and behavior policy for one logical agent role. The file is canonical even for promptless roles and may be intentionally empty to mean "no system prompt."

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

Secret-free setup bundles for one tool. The canonical file-backed payloads live under `.houmao/content/setups/`; the `.houmao/agents/tools/<tool>/setups/` tree is the compatibility projection that builders and runtime currently consume.

### `tools/<tool>/auth/<auth>/`

Local-only auth bundles for one tool. The canonical file-backed payloads live under `.houmao/content/auth/`; the `.houmao/agents/tools/<tool>/auth/<name>/` tree is the compatibility projection that legacy file-based flows still read.

### `compatibility-profiles/`

Optional compatibility metadata for specialized CAO or server-facing flows. `houmao-mgr project init` does not create this subtree by default; use `houmao-mgr project init --with-compatibility-profiles` when you want the optional root pre-created.

### `.houmao/mailbox/`

Optional project-local mailbox root. `houmao-mgr project init` does not create it by default. Enable it only when you want repo-scoped mailbox registrations and direct mailbox reads through `houmao-mgr project mailbox ...`.

## Committed vs. Local-Only

| Directory | Committed | Description |
|---|---|---|
| `.houmao/catalog.sqlite` | ❌ No | Canonical project-local semantic catalog |
| `.houmao/content/` | ❌ No | Managed prompt/auth/skill/setup payload store |
| `.houmao/agents/skills/` | ❌ No | Repo-local reusable capability packages |
| `.houmao/agents/roles/` | ❌ No | Repo-local role prompts and presets |
| `.houmao/agents/tools/<tool>/adapter.yaml` | ❌ No | Local copy of the tool projection and launch contract |
| `.houmao/agents/tools/<tool>/setups/` | ❌ No | Local copy of secret-free setup bundles |
| `.houmao/agents/tools/<tool>/auth/` | ❌ No | Local-only auth bundles |
| `.houmao/agents/compatibility-profiles/` | ❌ No | Optional local compatibility metadata, not created by default |
| `.houmao/mailbox/` | ❌ No | Optional project-local mailbox root |

Generated runtime homes and manifests are also disposable. If the runtime later creates `.houmao/jobs/` under the repo root, that scratch subtree is still runtime-local scratch, not tracked project source.

## How The Pieces Connect

1. Houmao persists project-local semantic objects in `.houmao/catalog.sqlite` and stores prompt/auth/skill/setup payloads under `.houmao/content/`.
2. When current builders or launchers need a file tree, Houmao materializes the `.houmao/agents/` compatibility projection from the catalog plus managed content refs.
3. `houmao-mgr agents launch --agents <role> --provider <provider>` resolves that role to `roles/<role>/presets/<tool>/default.yaml` inside the projection.
4. The resolved preset selects skills, setup, default auth, and optional launch/mailbox settings.
5. `BrainBuilder` combines the preset with `tools/<tool>/adapter.yaml`, the selected setup bundle, and the effective auth bundle to materialize a runtime home.
6. The runtime pairs the built manifest with `roles/<role>/system-prompt.md` and launches the session on the requested backend.

## Authoring Paths

The compatibility `.houmao/agents/` tree can still be inspected directly, but project-local truth now lives in the catalog and managed content store. The main UX layers are:

- `project easy specialist create ...` is the primary project-local authoring path when you want one reusable specialist persisted into the catalog and projected into the compatibility tree.
- `project easy instance launch|stop ...` is the higher-level runtime lifecycle path when you want to materialize or stop managed-agent instances from those compiled specialists.
- `project agents ...` is the low-level maintenance surface when you want to inspect or mutate the compatibility projection directly.
