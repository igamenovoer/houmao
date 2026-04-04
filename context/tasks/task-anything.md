# Redesign Prep: Current `houmao-mgr project` And Agent Definition Structure

> Superseded note: the implementation target is now `openspec/changes/reframe-project-cli-views/`.
> The old `project agent-tools` direction documented below is retained only as historical baseline context.

We want to redesign the `houmao-mgr project` subcommand and the agent definition directory so it is more intuitive and takes less effort for users to create their own agents.

This note documents the current design only. It is a baseline for later redesign work.

## Current `houmao-mgr project` Command Surface

Current top-level command tree:

```text
houmao-mgr project
├── init
├── status
└── agent-tools
    ├── claude
    │   └── auth
    │       ├── add
    │       ├── get
    │       ├── list
    │       ├── remove
    │       └── set
    ├── codex
    │   └── auth
    │       ├── add
    │       ├── get
    │       ├── list
    │       ├── remove
    │       └── set
    └── gemini
        └── auth
            ├── add
            ├── get
            ├── list
            ├── remove
            └── set
```

What the command group does today:

- `project init` bootstraps a repo-local `.houmao/` overlay in the current directory.
- `project status` reports whether a project overlay was discovered and what agent definition root is currently active.
- `project agent-tools <tool> auth ...` is only for CRUD on local auth bundles under `.houmao/agents/tools/<tool>/auth/`.

What it does not do today:

- It does not create a role.
- It does not create a skill.
- It does not create a preset.
- It does not scaffold a full runnable agent definition.
- It does not offer one command that says “create me an agent” or “create a project agent template”.

## Current Agent Definition Root Resolution

Commands that need an agent definition directory resolve it in this order:

1. explicit CLI `--agent-def-dir`
2. `AGENTSYS_AGENT_DEF_DIR`
3. nearest ancestor `.houmao/houmao-config.toml`
4. legacy `<pwd>/.agentsys/agents`

For repo-local workflows, the intended path is the discovered `.houmao/agents` directory.

## Current Project Overlay Created By `project init`

`houmao-mgr project init` creates or validates this structure:

```text
<repo>/
└── .houmao/
    ├── .gitignore
    ├── houmao-config.toml
    └── agents/
        ├── skills/
        ├── roles/
        ├── tools/
        └── compatibility-profiles/
```

Important current behavior:

- `.houmao/.gitignore` contains `*`, so the whole overlay is local-only by default.
- `houmao-config.toml` currently contains `schema_version = 1` and points `paths.agent_def_dir` to `agents`.
- `project init` creates empty authoring roots for `skills/`, `roles/`, and `compatibility-profiles/`.
- `project init` copies packaged starter assets only for `tools/`.
- `project init` also creates empty `auth/` roots for supported tools.

Packaged starter assets currently include:

- `tools/claude/adapter.yaml`
- `tools/claude/setups/default/...`
- `tools/codex/adapter.yaml`
- `tools/codex/setups/default/...`
- `tools/codex/setups/yunwu-openai/...`
- `tools/gemini/adapter.yaml`
- `tools/gemini/setups/default/...`

## Current Agent Definition Directory Shape

The canonical current layout, as documented and exercised by `tests/fixtures/agents`, is:

```text
agents/
├── skills/
│   └── <skill>/
│       └── SKILL.md
├── roles/
│   └── <role>/
│       ├── README.md                # optional in practice
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
│           └── <auth>/
│               ├── env/
│               │   └── vars.env
│               └── files/
│                   └── ...
└── compatibility-profiles/
```

In the current design, the user-facing concepts are split across three different top-level trees:

- `roles/` defines behavior and launch presets.
- `skills/` defines reusable capability packages.
- `tools/` defines tool contracts, tracked setups, and local auth bundles.

## Current Meaning Of Each Directory

### `skills/`

Each skill is a directory named by skill id, with a required `SKILL.md`.

Example:

```text
skills/openspec-apply-change/SKILL.md
skills/skill-invocation-probe/SKILL.md
```

Some skills may also carry extra reference material:

```text
skills/skill-invocation-probe/
├── SKILL.md
└── references/
    └── contract.md
```

### `roles/`

Each role is a logical agent role. The role owns:

- `system-prompt.md`
- optional `README.md`
- `presets/<tool>/<setup>.yaml`

Examples from the fixture tree:

- `roles/gpu-kernel-coder/`
- `roles/projection-demo/`
- `roles/mailbox-demo/`
- `roles/server-api-smoke/`

### `roles/<role>/system-prompt.md`

This is the role prompt and behavior policy. It is independent of any specific tool setup or auth bundle.

### `roles/<role>/presets/<tool>/<setup>.yaml`

This is the declarative launch preset for one role/tool/setup combination.

The file path itself defines:

- `role`
- `tool`
- `setup`

The YAML stores only non-path-derived data. Current supported top-level fields are:

- `skills`
- `auth`
- `launch`
- `mailbox`
- `extra`

Typical current preset examples look like:

```yaml
skills:
- openspec-apply-change
- openspec-verify-change
auth: personal-a-default
launch:
  prompt_mode: unattended
```

There is no separate top-level “agent” file today. The effective agent definition is spread across:

- role prompt
- preset YAML
- referenced skills
- referenced tool adapter
- referenced setup bundle
- referenced auth bundle

### `tools/<tool>/adapter.yaml`

This is the per-tool projection and launch contract.

It defines things like:

- which env var selects the runtime home
- which executable launches the tool
- where setup files project into the runtime home
- where skills project into the runtime home
- where auth files project into the runtime home
- which auth env vars are allowed
- optional tool-specific launch metadata

Current examples:

- `tools/codex/adapter.yaml`
- `tools/claude/adapter.yaml`
- `tools/gemini/adapter.yaml`

### `tools/<tool>/setups/<setup>/`

This is the checked-in, secret-free setup bundle for one tool variant.

Examples:

- `tools/codex/setups/default/config.toml`
- `tools/codex/setups/yunwu-openai/config.toml`
- `tools/claude/setups/default/settings.json`
- `tools/gemini/setups/default/README.md`

### `tools/<tool>/auth/<auth>/`

This is the local-only auth bundle for one tool/account/profile.

The current auth bundle layout is tool-specific, but commonly includes:

- `env/vars.env`
- optional `files/...`

Examples from fixtures:

```text
tools/codex/auth/personal-a-default/
├── env/vars.env
└── files/auth.json

tools/codex/auth/yunwu-openai/
└── env/vars.env

tools/claude/auth/kimi-coding/
├── env/vars.env
└── files/
    ├── claude_state.template.json
    └── credentials.json

tools/gemini/auth/personal-a-default/
├── env/vars.env
└── files/
    ├── credentials.json
    └── oauth_creds.json
```

### `compatibility-profiles/`

This is optional compatibility metadata used by specialized flows. It is part of the current source layout, but not part of the main authoring path for a typical user.

## Current User Workflow To Create A New Agent

Today, creating a new repo-local agent is a manual multi-step process:

1. Run `pixi run houmao-mgr project init`.
2. Add an auth bundle with `pixi run houmao-mgr project agent-tools <tool> auth add ...`.
3. Manually create `skills/<skill>/SKILL.md`.
4. Manually create `roles/<role>/system-prompt.md`.
5. Manually create `roles/<role>/presets/<tool>/<setup>.yaml`.
6. Build with `pixi run houmao-mgr brains build --preset ...` or launch with `pixi run houmao-mgr agents launch --agents <role> --provider <provider>`.

The quickstart example for the manual authoring step is effectively:

```text
.houmao/agents/skills/notes/SKILL.md
.houmao/agents/roles/researcher/system-prompt.md
.houmao/agents/roles/researcher/presets/claude/default.yaml
```

This means `project init` only gets the user to an empty shell plus tool scaffolding. The user still has to understand and manually assemble the role, skill, preset, setup, and auth model.

## Current Build And Launch Wiring

Current wiring across the system is:

1. Parse `skills/`, `roles/`, and `tools/` into an in-process catalog.
2. Resolve a role selector plus provider into `roles/<role>/presets/<tool>/<setup>.yaml`.
3. Read `skills` and optional `auth` from that preset.
4. Read the tool contract from `tools/<tool>/adapter.yaml`.
5. Read the setup bundle from `tools/<tool>/setups/<setup>/`.
6. Read the auth bundle from `tools/<tool>/auth/<auth>/`.
7. Materialize a runtime home from those pieces.
8. Pair the built home with `roles/<role>/system-prompt.md` at launch time.

## Current Structural Observations Relevant To Redesign

These are the current-state facts that matter for redesign:

- The user-visible concept “an agent” is not stored in one place.
- The `project` command manages overlay bootstrap and auth bundles, but not full agent creation.
- The current directory shape is strongly normalized for internal composition, but not optimized for first-time authoring.
- Role identity, tool identity, setup identity, skills, and auth are distributed across path conventions and separate directories.
- Preset identity is partially encoded in directory names instead of file contents.
- A user must understand both tracked tool setup bundles and local auth bundles before they can create a runnable agent.
