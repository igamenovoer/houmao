# Easy Specialists

Easy specialists are lightweight, project-local agent definitions that bundle everything needed to launch an agent — role, tool, credentials, skills, and launch configuration — into a single named configuration.

## When to Use Easy Specialists vs Full Presets

| Approach | Best For |
|---|---|
| **Easy specialist** | Quick setup, single-tool agents, operators who want an opinionated default path. One command creates a complete launchable agent definition. |
| **Full role/preset** | Fine-grained control, multi-tool roles, shared preset libraries, custom adapter configurations. Requires manual setup of `roles/`, `tools/`, and `skills/` directories. |

An easy specialist is a convenience layer over the full preset system. Under the hood, `specialist create` generates the same directory structure (`roles/<name>/`, `tools/<tool>/auth/<creds>/`, preset YAML) that the low-level `project agents` commands produce — it just does it in one step.

## Specialist → Instance → Managed Agent

```
┌────────────────────────┐
│  SPECIALIST (template)  │
│  name, tool, creds,     │
│  skills, launch config  │
└──────────┬─────────────┘
           │ instance launch
           ▼
┌────────────────────────┐
│  INSTANCE (runtime)     │
│  tmux session, brain    │
│  home, registry entry   │
└──────────┬─────────────┘
           │ = managed agent
           ▼
┌────────────────────────┐
│  MANAGED AGENT          │
│  controllable via       │
│  agents prompt/stop/    │
│  gateway/mail/...       │
└────────────────────────┘
```

- A **specialist** is a stored definition (template). It lives in the project catalog at `.houmao/catalog.sqlite` with content under `.houmao/content/`.
- An **instance** is a running agent launched from a specialist. It gets its own tmux session, brain home, and registry entry.
- An instance IS a managed agent — it appears in `agents list`, can be targeted by `agents prompt`, `agents gateway`, `agents mail`, and all other managed-agent commands.

## Creating a Specialist

```bash
houmao-mgr project easy specialist create \
  --name my-reviewer \
  --tool claude \
  --system-prompt-file ./prompts/reviewer.md \
  --api-key "$ANTHROPIC_API_KEY"
```

Key options:

| Option | Default | Description |
|---|---|---|
| `--name` | Required | Specialist name. Used as the role name and default credential name. |
| `--tool` | Required | Tool lane: `claude`, `codex`, or `gemini`. |
| `--system-prompt` / `--system-prompt-file` | None | Inline prompt text or path to a prompt markdown file. |
| `--credential` | `<name>-creds` | Auth bundle name. Defaults to `<specialist-name>-creds`. |
| `--api-key` | None | API key for the selected tool. |
| `--setup` | `default` | Preset setup name within the tool's setup bundles. |
| `--with-skill` | None | Repeatable. Path to a skill directory (must contain `SKILL.md`). |
| `--env-set` | None | Repeatable. Persistent environment variable as `NAME=value`. |
| `--no-unattended` | False | Use `prompt_mode: as_is` instead of the default `unattended` mode. |

Tool-specific credential options are also available: `--claude-auth-token`, `--claude-model`, `--codex-org-id`, `--google-api-key`, etc.

Gemini-specific auth inputs now support two maintained lanes:

- API-key lane: `--api-key` with optional `--base-url` to persist `GEMINI_API_KEY` plus `GOOGLE_GEMINI_BASE_URL`.
- OAuth lane: `--gemini-oauth-creds /path/to/oauth_creds.json` to persist the Gemini CLI OAuth credential file. You can also combine this with the API-key lane in one specialist or auth bundle; Houmao preserves explicit API-key and endpoint settings instead of overwriting them.

Gemini easy specialists now follow the same easy unattended default as Claude and Codex: by default Houmao persists `launch.prompt_mode: unattended`, and `--no-unattended` remains the explicit opt-out to `as_is`. Gemini stays headless-only on the easy instance surface, so launch Gemini specialists with `houmao-mgr project easy instance launch --headless`.

Example Gemini specialist:

```bash
houmao-mgr project easy specialist create \
  --name gemini-reviewer \
  --tool gemini \
  --system-prompt "You are a Gemini-based code reviewer." \
  --api-key "$GEMINI_API_KEY" \
  --base-url https://gemini.example.test \
  --gemini-oauth-creds ./secrets/oauth_creds.json
```

## Launching an Instance

```bash
houmao-mgr project easy instance launch \
  --specialist my-reviewer \
  --name reviewer-1
```

Key options:

| Option | Default | Description |
|---|---|---|
| `--specialist` | Required | Specialist name to launch from. |
| `--name` | Required | Managed-agent instance name. |
| `--headless` | False | Launch in detached/background mode. |
| `--yolo` | False | Skip workspace trust confirmation. |
| `--session-name` | None | Optional tmux session name override. |
| `--auth` | Specialist's credential | Optional auth bundle override. |
| `--env-set` | None | Repeatable. One-off launch environment variable. |
| `--mail-transport` | None | Mailbox transport: `filesystem`. |
| `--mail-root` | None | Shared filesystem mailbox root (when using mailbox). |

Gemini specialists remain headless-only here. Use `--headless` when launching a Gemini specialist through `project easy instance launch`.

## Managing Specialists and Instances

```bash
# List all specialists in the project
houmao-mgr project easy specialist list

# Inspect one specialist's configuration
houmao-mgr project easy specialist get --name my-reviewer

# Remove a specialist definition
houmao-mgr project easy specialist remove --name my-reviewer

# List active instances
houmao-mgr project easy instance list

# Inspect one instance's state
houmao-mgr project easy instance get --name reviewer-1

# Stop an instance
houmao-mgr project easy instance stop --name reviewer-1
```

## Storage Layout

Specialist data is stored across two locations within the project overlay:

| Location | Content |
|---|---|
| `.houmao/catalog.sqlite` | Specialist metadata: name, tool, provider, credentials, skills, launch config. |
| `.houmao/content/prompts/<name>.md` | System prompt file. |
| `.houmao/content/auth/<tool>/<credential>/` | Auth bundle directory tree. |
| `.houmao/content/skills/<skill>/` | Skill directory copies. |
| `.houmao/agents/roles/<name>/` | Generated role projection with `system-prompt.md` and `presets/` subdirectory. |

## See Also

- [houmao-mgr project easy](../reference/cli/houmao-mgr.md) — CLI reference for project easy commands
- [Agent Definition Directory](agent-definitions.md) — full directory structure reference
- [Project-Aware Operations](../reference/agents/operations/project-aware-operations.md) — how commands resolve project context
