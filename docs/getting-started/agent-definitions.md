# Agent Definition Directory

The **agent definition directory** is the canonical source of truth for everything Houmao needs to build and run agent brains. It contains tool adapters, skills, configuration profiles, credentials, recipes, roles, and blueprints — organized by responsibility and split between committed repository assets and local-only secrets.

The default location is `.agentsys/agents/` (override with the `AGENTSYS_AGENT_DEF_DIR` environment variable). The best starting template is `tests/fixtures/agents/`.

## Directory Layout

```
<agent-def-dir>/
├── blueprints/                          # Recipe + role bindings (YAML)
│   ├── gpu-kernel-coder-claude.yaml
│   └── ...
├── brains/
│   ├── tool-adapters/                   # Per-tool build & launch contracts (YAML)
│   │   └── <tool>.yaml
│   ├── skills/                          # Reusable capability packages
│   │   └── <name>/SKILL.md
│   ├── cli-configs/                     # Secret-free tool config profiles
│   │   ├── claude/default/settings.json
│   │   ├── codex/default/config.toml
│   │   └── gemini/default/...
│   ├── api-creds/                       # Local-only credentials (GITIGNORED)
│   │   ├── claude/<profile>/env/vars.env
│   │   ├── codex/<profile>/env/vars.env
│   │   └── gemini/<profile>/env/vars.env
│   └── brain-recipes/                   # Declarative presets (YAML)
│       ├── claude/<name>.yaml
│       ├── codex/<name>.yaml
│       └── gemini/<name>.yaml
├── roles/                               # Role prompt packages
│   └── <role>/system-prompt.md
└── compatibility-profiles/              # Optional compatibility metadata
```

## Directory Reference

### `brains/tool-adapters/` — Per-Tool Build & Launch Contracts *(required)*

Each supported CLI tool (e.g., `claude`, `codex`, `gemini`) has a YAML adapter file that defines its build-time and launch-time contract. The adapter tells `BrainBuilder` how to:

- Locate the tool's launch executable
- Inject environment variables (the `env_injection_mode`)
- Map credential files from the agent definition directory into the runtime home
- Apply tool-specific launch arguments

Tool adapters are the foundation of the build phase. Without an adapter for a given tool, no brain can be built for it.

### `brains/skills/` — Reusable Capability Packages *(required per recipe)*

Skills are self-contained capability modules that get projected into the agent's runtime home during the build phase. Each skill lives in its own subdirectory and must contain a `SKILL.md` file that describes the capability in a format the target agent CLI can consume.

Skills are referenced by name in brain recipes and build requests. A recipe might select `["code-review", "testing", "documentation"]` from the available skill pool. Only the selected skills are materialized into the runtime home.

### `brains/cli-configs/` — Secret-Free Tool Config Profiles *(required per recipe)*

Configuration profiles contain tool-specific settings files that are safe to commit to version control. These are projected into the runtime home during build, providing the agent CLI with its working configuration.

The directory structure is `cli-configs/<tool>/<profile>/`, where:

- `<tool>` matches the tool adapter name (e.g., `claude`, `codex`, `gemini`)
- `<profile>` is a named configuration variant (e.g., `default`, `restricted`, `full-access`)

Examples:

- `cli-configs/claude/default/settings.json` — Claude CLI settings
- `cli-configs/codex/default/config.toml` — Codex CLI configuration

**These files must never contain secrets.** API keys, tokens, and credentials belong in `api-creds/`.

### `brains/api-creds/` — Local-Only Credentials *(gitignored, required per recipe)*

Credential profiles contain the secret material (API keys, authentication tokens, environment variable files) needed to actually run the agent CLI. These are **never committed** — the directory is excluded via `.gitignore` and `pyproject.toml`.

The directory structure mirrors `cli-configs/`: `api-creds/<tool>/<profile>/env/vars.env`. During the build phase, `BrainBuilder` copies the selected credential profile into the runtime home according to the mappings defined in the tool adapter.

Each developer must populate their own `api-creds/` directory locally. The structure is documented here and in the tool adapter files so the required files are discoverable.

### `brains/brain-recipes/` — Declarative Presets *(recommended)*

A brain recipe is a YAML file that bundles a complete build specification into a single reusable preset:

- **`tool`**: Which CLI tool to target
- **`skills`**: List of skill names to include
- **`config_profile`**: Which secret-free config profile to use
- **`credential_profile`**: Which local credential profile to use
- **`launch_overrides`**: Optional secret-free launch argument overrides

Recipes live under `brain-recipes/<tool>/<name>.yaml`. They are the recommended way to define reproducible brain builds — instead of passing `--tool`, `--skill`, `--config-profile`, and `--cred-profile` individually, you point at a recipe file.

### `roles/` — Role Prompt Packages *(required)*

A role defines the system prompt and behavior policy for an agent session. Each role lives in its own subdirectory and must contain a `system-prompt.md` file.

Roles are paired with built brains at launch time. The `RuntimeSessionController` reads the role's system prompt and applies it to the session using a backend-specific injection strategy (native developer instructions for Codex, appended system prompt for Claude, bootstrap message for Gemini, etc.).

### `blueprints/` — Recipe + Role Bindings *(recommended)*

Blueprints bind a brain recipe to a role in a single YAML file, providing a complete "build and run" specification. Instead of separately specifying `--recipe` and `--role`, you can reference a blueprint that pairs them.

Blueprints are optional but recommended for standardized agent configurations that are used repeatedly.

### `compatibility-profiles/` — Optional Compatibility Metadata

Contains optional metadata about CLI version compatibility requirements. This supports the versioned launch policy system, which resolves unattended startup strategies against the installed CLI version and fails closed for unsupported versions.

## Committed vs. Local-Only

| Directory | Committed | Description |
|---|---|---|
| `brains/tool-adapters/` | ✅ Yes | Per-tool build contracts |
| `brains/skills/` | ✅ Yes | Capability packages |
| `brains/cli-configs/` | ✅ Yes | Secret-free configuration |
| `brains/brain-recipes/` | ✅ Yes | Declarative build presets |
| `brains/api-creds/` | ❌ No | Local-only credentials |
| `roles/` | ✅ Yes | Role prompt packages |
| `blueprints/` | ✅ Yes | Recipe + role bindings |
| `compatibility-profiles/` | ✅ Yes | Version compatibility metadata |

The generated runtime homes (under `tmp/` by default) are also gitignored. They contain projected copies of configs and credentials and are safe to delete and rebuild at any time.

## How the Pieces Connect

1. A **tool adapter** defines *how* to build and launch for a specific CLI tool.
2. **Skills**, **cli-configs**, and **api-creds** provide the *what* — the capabilities, settings, and secrets that get projected into the runtime home.
3. A **brain recipe** bundles a specific combination of tool + skills + config profile + credential profile into a reusable preset.
4. A **role** defines *who* the agent is — its system prompt and behavior policy.
5. A **blueprint** binds a recipe to a role for a complete "build and launch" specification.

During the **build phase**, `BrainBuilder` reads the recipe (or explicit parameters), resolves them against the agent definition directory using the tool adapter, and materializes a runtime home with all the projected files. During the **run phase**, the runtime home is paired with a role and dispatched to a backend.
