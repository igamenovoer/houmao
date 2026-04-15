# Architecture Overview

Houmao orchestrates CLI-based agents (Codex, Claude, Gemini) as real tmux-backed processes with isolated runtime homes. The lifecycle still has two phases. The reusable source model is `recipe + setup + auth`, and reusable birth-time launch configuration lives separately as **launch profiles** that compose with recipe defaults during build. In project overlays, auth selection is user-facing by display name while the catalog owns the stable underlying auth identity. Managed launches also prepend one short Houmao-owned prompt header by default after any prompt-overlay resolution and before backend-specific prompt injection. For the shared conceptual model that ties easy profiles and explicit launch profiles together, see [Launch Profiles](launch-profiles.md).

## Two-Phase Lifecycle

```mermaid
flowchart TD
    Op["Operator"] --> SRC["Source Tree<br/>(roles + recipes + launch-profiles +<br/>tools + skills)"]
    SRC --> CAT["Canonical Parsed Catalog"]
    CAT --> RLS["Resolved Launch Spec<br/>(tool, role, setup, skills, auth,<br/>launch-profile defaults)"]
    RLS --> BB["BrainBuilder"]
    BB --> BM["Brain Manifest<br/>(schema_version=4,<br/>launch-profile provenance)"]
    BM --> LP["LaunchPlanRequest<br/>(manifest + role)"]
    LP --> RT["Runtime Session<br/>Controller"]
```

## Build Phase

`src/houmao/agents/brain_builder.py` materializes a disposable runtime home from explicit inputs or one resolved preset.

### Key Types

**`BuildRequest`** captures what to build:

| Field | Description |
|---|---|
| `agent_def_dir` | Agent definition root |
| `tool` | CLI tool name |
| `skills` | Selected skill names |
| `setup` | Selected checked-in setup bundle |
| `auth` | Effective auth bundle |
| `preset_path` | Optional resolved preset path for provenance |
| `runtime_root` | Where to create the runtime home |
| `mailbox` | Optional mailbox binding |
| `agent_name` / `agent_id` / `home_id` | Launch-time identity metadata |

**`BuildResult`** captures what was built:

| Field | Description |
|---|---|
| `home_id` | Unique runtime-home id |
| `home_path` | Materialized runtime home |
| `manifest_path` | Emitted brain manifest path |
| `launch_helper_path` | Generated launch helper |
| `launch_preview` | Human-readable launch command |
| `manifest` | Full manifest payload |

**`AgentPreset`** is the parsed declarative preset stored at `presets/<name>.yaml`.

**`ToolAdapter`** is the per-tool projection and launch contract stored at `tools/<tool>/adapter.yaml`.

## Run Phase

`src/houmao/agents/realm_controller/` reads the built manifest, pairs it with a role package, and resolves a backend-specific `LaunchPlan`.

### Key Types

**`LaunchPlanRequest`**

| Field | Description |
|---|---|
| `brain_manifest` | Built manifest from the build phase |
| `role_package` | Role name and system prompt |
| `backend` | Target backend kind |
| `working_directory` | Session working directory |

**`LaunchPlan`**

| Field | Description |
|---|---|
| `backend` | Target backend kind |
| `tool` | CLI tool name |
| `executable` | Tool executable |
| `args` | Final launch args |
| `working_directory` | Session working directory |
| `home_env_var` / `home_path` | Runtime-home selector |
| `env` | Final environment map |
| `role_injection` | Backend-specific prompt injection plan |
| `mailbox` | Optional resolved mailbox config |

## Source Layout

| Path | Responsibility |
|---|---|
| `src/houmao/agents/definition_parser.py` | Parse `agents/` source tree inputs into the canonical in-memory catalog used by non-project build flows |
| `src/houmao/agents/native_launch_resolver.py` | Resolve `--agents` selectors onto presets |
| `src/houmao/agents/brain_builder.py` | Build phase: resolved inputs -> runtime home + manifest |
| `src/houmao/agents/realm_controller/launch_plan.py` | Manifest + role -> backend launch plan |
| `src/houmao/agents/realm_controller/backends/` | Backend implementations |
| `src/houmao/srv_ctrl/commands/agents/core.py` | `houmao-mgr agents launch` preset-backed flow |

## Project CLI Views

The repo-local operator surface is intentionally split into one low-level view and two user-facing convenience views:

```text
houmao-mgr project
├── init | status
├── agents
│   ├── roles ...
│   ├── recipes ...                # canonical low-level source recipes
│   ├── presets ...                # compatibility alias for `recipes`
│   ├── launch-profiles ...        # explicit recipe-backed birth-time launch profiles
│   └── tools <tool> ...
├── easy
│   ├── specialist ...
│   ├── profile ...                # specialist-backed easy birth-time profiles
│   └── instance ...
└── mailbox
    ├── init | status | register | unregister | repair | cleanup
    ├── accounts list|get
    └── messages list|get
```

- `project agents ...` is the low-level compatibility-projection surface for `.houmao/agents/`. Project-local semantic truth lives in `.houmao/catalog.sqlite` plus `.houmao/content/`, while `.houmao/agents/` remains the generated file-tree view consumed by current builders and runtime.
- `project easy ...` lets users author reusable specialists, optional specialist-backed easy profiles, and view running instances without hand-editing the tree.
- `project mailbox ...` mirrors the generic `houmao-mgr mailbox ...` operations, but automatically targets `<project-root>/.houmao/mailbox`.

Project-aware commands select that overlay root through one shared contract:

- `HOUMAO_PROJECT_OVERLAY_DIR` selects an overlay root directly and wins over ambient discovery.
- Otherwise Houmao uses `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=ancestor` by default, which searches for the nearest ancestor `.houmao/houmao-config.toml` within the current Git boundary.
- Set `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only` to restrict ambient lookup to `<cwd>/.houmao/houmao-config.toml`.
