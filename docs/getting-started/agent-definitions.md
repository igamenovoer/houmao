# Agent Definition Directory

The **agent definition directory** is the source tree Houmao parses before it resolves selectors, builds runtime homes, or launches agents. The canonical layout is prompt-only roles plus named recipes, shared launch profiles, and tool-scoped setup/auth bundles. Auth display names are catalog metadata; the file-backed auth trees use opaque bundle refs internally.

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

CI or controlled automation can bypass the default `<cwd>/.houmao` location by setting `HOUMAO_PROJECT_OVERLAY_DIR=/abs/path`. When that env var is set, Houmao treats `/abs/path` itself as the overlay root and resolves `houmao-config.toml`, `catalog.sqlite`, `agents/`, and `mailbox/` directly under that directory.

Ambient overlay discovery is controlled separately by `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`:

- `ancestor` is the default and searches for the nearest ancestor `.houmao/houmao-config.toml`, stopping at the Git repository boundary.
- `cwd_only` skips parent search and inspects only `<cwd>/.houmao/houmao-config.toml`.

This discovery-mode env only affects ambient lookup. It does not override `HOUMAO_PROJECT_OVERLAY_DIR`.

Commands that need an agent-definition root resolve it with this precedence:

1. explicit CLI `--agent-def-dir`
2. `HOUMAO_AGENT_DEF_DIR`
3. `HOUMAO_PROJECT_OVERLAY_DIR`
4. ambient project-overlay discovery under `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`
5. default `<pwd>/.houmao/agents`

`HOUMAO_PROJECT_OVERLAY_DIR` must be an absolute path. If it points at an overlay that already contains `houmao-config.toml`, that selected overlay becomes the discovery anchor. If it points at an overlay directory without config yet, project-aware fallback paths come from `<overlay-root>/agents` until you initialize it. When `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` is unset, Houmao uses `ancestor`. When it is set to `cwd_only`, ambient discovery ignores parent overlays and falls back to `<cwd>/.houmao/agents` if no cwd-local overlay config exists.

Maintained project-aware local-state commands reuse that same active overlay for other defaults too: runtime state lands under `<active-overlay>/runtime`, managed-agent memory roots land under `<active-overlay>/memory/agents/<agent-id>/`, and filesystem mailbox state lands under `<active-overlay>/mailbox` unless an explicit CLI or env override wins first.

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
    │   │   └── <role>/system-prompt.md
    │   ├── presets/
    │   │   └── <recipe>.yaml
    │   ├── launch-profiles/
    │   │   └── <profile>.yaml
    │   ├── tools/
    │   │   └── <tool>/
    │   │       ├── adapter.yaml
    │   │       ├── setups/
    │   │       │   └── <setup>/...
    │   │       └── auth/
    │   │           └── <opaque-bundle-ref>/...
    └── mailbox/                      # optional, created only when mailbox workflows are enabled
```

`houmao-mgr project init` seeds the managed content roots and the SQLite catalog. It does not create `.houmao/agents/`, `.houmao/mailbox/`, or `.houmao/easy/` unless you opt into workflows that need those paths explicitly.

The repo-local project surface is intentionally split into three views:

- `houmao-mgr project agents ...` for low-level filesystem-oriented source management
- `houmao-mgr project easy ...` for higher-level specialist and instance authoring
- `houmao-mgr project mailbox ...` for project-scoped mailbox-root operations against `.houmao/mailbox`

## Directory Reference

### `catalog.sqlite`

The canonical semantic store for project-local specialists, roles, recipes, launch profiles, setup profiles, skill packages, auth profiles, and managed content references. Advanced operators can inspect stable read views such as `v_specialists`, `v_presets`, `v_launch_profiles`, and `v_content_refs` directly with SQLite tooling.

### `content/`

Managed file-backed payload storage. Large text blobs and tree-shaped payloads such as prompt files, auth bundles, skill packages, and setup bundles live here even though their semantic relationships are owned by `catalog.sqlite`.

### `skills/`

Reusable capability packages projected into runtime homes. Under `.houmao/agents/` this is now a compatibility projection fed from `catalog.sqlite` and `.houmao/content/`.

### `roles/<role>/system-prompt.md`

The role prompt and behavior policy for one logical agent role. The file is canonical even for promptless roles and may be intentionally empty to mean "no system prompt."

### `presets/<recipe>.yaml`

The compatibility-projected declarative recipe file. The filename supplies the recipe name, and the YAML stores:

- required `role`
- required `tool`
- required `setup`
- `skills`
- optional `auth`
- optional `launch`
- optional `mailbox`
- optional `extra`

### `launch-profiles/<profile>.yaml`

The compatibility-projected reusable birth-time launch profile. Easy profiles and explicit launch profiles share the same underlying catalog model but remain distinct by source lane:

- easy profiles are specialist-backed and managed through `project easy profile ...`
- explicit launch profiles are recipe-backed and managed through `project agents launch-profiles ...`

For the shared conceptual model — easy versus explicit lanes, the precedence chain, prompt overlays, and profile provenance reporting — see [Launch Profiles](launch-profiles.md).

### `tools/<tool>/adapter.yaml`

The tool adapter defines how Houmao projects setup files, skills, and auth material into the runtime home, plus the tool-specific launch contract.

### `tools/<tool>/setups/<setup>/`

Secret-free setup bundles for one tool. The canonical file-backed payloads live under `.houmao/content/setups/`; the `.houmao/agents/tools/<tool>/setups/` tree is the compatibility projection that builders and runtime currently consume.

### `tools/<tool>/auth/<bundle-ref>/`

Local-only auth bundles for one tool. The canonical file-backed payloads live under `.houmao/content/auth/<tool>/<bundle-ref>/`; the `.houmao/agents/tools/<tool>/auth/<bundle-ref>/` tree is the compatibility projection that legacy file-based flows still read. The operator-facing auth name is stored separately in the catalog and can be renamed without changing these directory basenames.

### `.houmao/mailbox/`

Optional project-local mailbox root. `houmao-mgr project init` does not create it by default. Enable it only when you want repo-scoped mailbox registrations and direct mailbox reads through `houmao-mgr project mailbox ...`.

## Committed vs. Local-Only

| Directory | Committed | Description |
|---|---|---|
| `.houmao/catalog.sqlite` | ❌ No | Canonical project-local semantic catalog |
| `.houmao/content/` | ❌ No | Managed prompt/auth/skill/setup payload store |
| `.houmao/agents/skills/` | ❌ No | Repo-local reusable capability packages |
| `.houmao/agents/roles/` | ❌ No | Repo-local role prompts |
| `.houmao/agents/presets/` | ❌ No | Repo-local named recipes |
| `.houmao/agents/launch-profiles/` | ❌ No | Repo-local launch-profile projection |
| `.houmao/agents/tools/<tool>/adapter.yaml` | ❌ No | Local copy of the tool projection and launch contract |
| `.houmao/agents/tools/<tool>/setups/` | ❌ No | Local copy of secret-free setup bundles |
| `.houmao/agents/tools/<tool>/auth/` | ❌ No | Local-only auth bundles projected by opaque bundle ref |
| `.houmao/mailbox/` | ❌ No | Optional project-local mailbox root |

Generated runtime homes, manifests, mailbox state, and managed-agent memory are also local-only operator state. When maintained build and launch flows place runtime artifacts under `.houmao/runtime`, mailbox state under `.houmao/mailbox`, and memory roots under `.houmao/memory/agents/<agent-id>/`, those subtrees remain overlay-local runtime state rather than tracked project source.

## How The Pieces Connect

1. Houmao persists project-local semantic objects in `.houmao/catalog.sqlite` and stores prompt/auth/skill/setup payloads under `.houmao/content/`.
2. When current builders or launchers need a file tree, Houmao materializes the `.houmao/agents/` compatibility projection from the catalog plus managed content refs.
3. `houmao-mgr agents launch --agents <role> --provider <provider>` resolves that role to the unique named preset whose YAML declares the matching `role`, provider-derived `tool`, and `setup: default`.
4. The resolved preset selects skills, setup, default auth, and optional launch/mailbox settings, including durable `launch.env_records` when present. If `launch.prompt_mode` is omitted, current build and launch flows resolve that omission to the unattended default; use `as_is` explicitly for pass-through startup posture.
5. `BrainBuilder` combines the recipe with `tools/<tool>/adapter.yaml`, the selected setup bundle, the effective auth bundle, launch-profile-owned prompt or mailbox defaults when present, and any durable `launch.env_records` to materialize a runtime home.
6. The runtime pairs the built manifest with `roles/<role>/system-prompt.md` and launches the session on the requested backend.

## Authoring Paths

The compatibility `.houmao/agents/` tree can still be inspected directly, but project-local truth now lives in the catalog and managed content store. The main UX layers are:

- `project easy specialist create ...` is the primary project-local authoring path when you want one reusable specialist persisted into the catalog and projected into the compatibility tree.
- `project easy profile ...` is the higher-level authoring path when you want reusable specialist-backed birth-time defaults without duplicating the specialist itself.
- `project agents recipes ...` is the canonical low-level authoring path for named recipes; `project agents presets ...` remains the compatibility alias for the same resources.
- `project agents launch-profiles ...` is the low-level authoring path for reusable recipe-backed birth-time launch profiles.
- for maintained easy launch paths, `project easy specialist create ...` persists unattended launch posture by default; pass `--no-unattended` to persist `launch.prompt_mode: as_is` instead.
- persistent non-credential launch env belongs to specialist config via repeatable `project easy specialist create --env-set NAME=value`, which projects into `launch.env_records` and survives relaunch.
- `project easy instance launch|stop ...` is the higher-level runtime lifecycle path when you want to materialize or stop managed-agent instances from those compiled specialists.
- one-off runtime env belongs to `project easy instance launch --env-set NAME=value|NAME`; it applies to the current live session only and is dropped by relaunch.
- `project agents ...` is the low-level maintenance surface when you want to inspect or mutate the compatibility projection directly.
