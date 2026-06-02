# Project-Aware Operations

Most stateful local `houmao-mgr` workflows discover and use an active `.houmao/` project overlay for native-agent projection, runtime root binding, managed-agent memory binding, and mailbox root binding. Ordinary project-backed commands require an initialized or explicitly selected overlay; they do not bootstrap `<cwd>/.houmao` except through `houmao-mgr project init`.

## Resolution Precedence

### Project Overlay Resolution

The project overlay directory is resolved in this order:

| Priority | Source | Description |
|---|---|---|
| 1 | `HOUMAO_PROJECT_OVERLAY_DIR` | Environment variable. Must be an absolute path pointing directly at the overlay directory. |
| 2 | Ambient discovery under `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` | Defaults to `ancestor`, which searches the nearest ancestor `.houmao/houmao-config.toml` from cwd and stops at the Git repository boundary. Set `cwd_only` to inspect only `<cwd>/.houmao/houmao-config.toml`. |
| 3 | `<cwd>/.houmao/` | Default fallback candidate when no overlay config is discovered. May not exist on disk. |

`HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` affects ambient discovery only. It does not override `HOUMAO_PROJECT_OVERLAY_DIR`.

### Native-Agent Projection Resolution

Within the resolved project overlay, the native-agent compatibility projection directory is resolved separately:

| Priority | Source | Description |
|---|---|---|
| 1 | `--agent-def-dir` CLI flag | Explicit CLI argument, when available. |
| 2 | `houmao-config.toml` `[paths] agent_def_dir` | Setting from the project overlay configuration. |
| 3 | `<overlay_root>/agents` | Fallback when an overlay root was selected but config was not loaded. |

Direct provider-aligned native-agent commands do not use project discovery. Use `houmao-mgr internals native-agent ... --native-agent-root <path>` or `HOUMAO_NATIVE_AGENT_ROOT` for that lower-level surface.

## What Project Context Provides

When a project overlay is discovered, commands receive `ProjectAwareLocalRoots` containing:

| Root | Default Location | Description |
|---|---|---|
| `overlay_root` | `.houmao/` | The project overlay directory. |
| `agent_def_dir` | `.houmao/agents/` | Native-agent compatibility projection (tools, roles, skills, recipes, launch dossiers). |
| `runtime_root` | `.houmao/runtime/` | Session runtime state and build artifacts. |
| `memory_root` | `.houmao/memory/` | Root for managed-agent memory envelopes, including `houmao-memo.md` and `pages/`. |
| `jobs_root` | `.houmao/jobs/` | Legacy job tracking root retained for older internal and demo flows; not the current managed-agent memory contract. |
| `mailbox_root` | `.houmao/mailbox/` | Project-local filesystem mailbox root. |
| `specialists_root` | `.houmao/easy/specialists/` | Project specialist metadata. |

Each root can be overridden independently by its global environment variable:

| Root | Global Override |
|---|---|
| `runtime_root` | `HOUMAO_GLOBAL_RUNTIME_DIR` |
| `mailbox_root` | `HOUMAO_GLOBAL_MAILBOX_DIR` |
| `jobs_root` | `HOUMAO_LOCAL_JOBS_DIR` legacy non-workspace job tracking only |

## Catalog-Backed Storage

The project overlay includes a SQLite catalog at `.houmao/catalog.sqlite` (managed by `ProjectCatalog`) that stores:

- **Specialist definitions**: Project specialist metadata including tool, auth selection, skills, and launch configuration.
- **Auth profiles**: Catalog-owned auth identities with mutable display names, stable opaque bundle refs, and managed content references under `.houmao/content/auth/`.
- **Project profiles**: Reusable birth-time launch configuration for `project profile ...`, including optional prompt overlay, gateway mail-notifier appendix default, and memo seed references. Direct `internals native-agent launch-dossiers ...` edits native files and does not update the project catalog.
- **Managed content references**: Pointers to prompt files, auth bundles, skill trees, setup trees, and prompt-overlay files stored under `.houmao/content/`.
- **Role, recipe, launch-dossier, and auth projections**: Generated native-agent tree entries used during build and launch (`.houmao/agents/roles/`, `.houmao/agents/presets/`, `.houmao/agents/launch-profiles/`, `.houmao/agents/tools/<tool>/auth/<bundle-ref>/`).

The catalog is initialized during `project init` and is the authoritative source for project-local auth, specialist, and project-profile relationships. The `.houmao/agents/` tree is a derived compatibility projection rather than the semantic source of truth for ordinary project workflows.

## Which Commands Are Project-Aware

| Command Family | Project Context Used |
|---|---|
| `agents launch` / `agents join` | Agent definitions, runtime root, managed-agent memory root, mailbox root |
| `brains build` | Agent definitions (with optional `--agent-def-dir` override) |
| `agents list` / `agents state` | Runtime root for shared registry discovery |
| `agents mailbox register` | Mailbox root defaults to project overlay |
| `project *` | Full overlay resolution and catalog access |
| `mailbox *` | Mailbox root from project overlay |
| `server start` | Runtime root for server state |
| `admin cleanup` | Runtime root for cleanup targeting |

## Environment Overrides for CI

In CI or controlled automation where no `.houmao/` directory exists on disk:

- Set `HOUMAO_PROJECT_OVERLAY_DIR` to point at a pre-built overlay directory.
- Set `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only` when you want subdirectory-local commands to ignore a parent overlay and consider only `<cwd>/.houmao`.
- For direct provider-aligned native-agent material, use `internals native-agent ... --native-agent-root <path>` or set `HOUMAO_NATIVE_AGENT_ROOT`.
- Set `HOUMAO_GLOBAL_RUNTIME_DIR` to use a shared runtime root instead of the project-local one.

## See Also

- [Agent Definition Directory](../../getting-started/agent-definitions.md) — overlay directory structure
- [Managed Agent Memory](../../getting-started/managed-memory-dirs.md) — operator-facing guide to memory roots, free-form memo files, and pages
- [System Files Reference](index.md) — filesystem paths reference
- [Specialists Guide](../../getting-started/easy-specialists.md) — the project specialist/profile model
