# Recipes and Adapters

The build phase resolves three declarative artifacts — brain recipes, tool adapters, and blueprints — to determine what gets projected into a runtime home.

## BrainRecipe

A `BrainRecipe` is a frozen dataclass that serves as a declarative preset for building a brain. It selects a tool, a subset of skills, and the config/credential profiles to use.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Recipe name |
| `tool` | `str` | Tool identifier (`codex`, `claude`, `gemini`) |
| `skills` | `list[str]` | Skill paths or names to include |
| `config_profile` | `str` | Config profile name |
| `credential_profile` | `str` | Credential profile name |
| `launch_overrides` | `LaunchOverrides \| None` | Optional launch argument/parameter overrides |
| `operator_prompt_mode` | `OperatorPromptMode \| None` | Controls operator prompt injection behavior |
| `default_agent_name` | `str \| None` | Default canonical agent name for sessions built from this recipe |
| `mailbox` | `MailboxDeclarativeConfig \| None` | Mailbox configuration for inter-agent messaging |

### Recipe Files

Recipes are YAML files stored under `brains/brain-recipes/<tool>/` in the agent definition directory.

Example recipe:

```yaml
schema_version: 1
name: my-recipe
tool: claude
skills: [coding-assistant]
config_profile: default
credential_profile: personal-a-default
```

Recipes are loaded via `load_brain_recipe(path)` which validates the YAML against the expected schema and returns a `BrainRecipe` instance.

## ToolAdapter

A `ToolAdapter` is a frozen dataclass that defines the build and launch contract for a specific CLI tool. It tells the brain builder how to project files into the runtime home and how to invoke the tool at launch time.

| Field | Type | Description |
|---|---|---|
| `tool` | `str` | Tool identifier |
| `home_selector_env_var` | `str` | Environment variable pointing to the runtime home (e.g., `CODEX_HOME`, `CLAUDE_HOME`) |
| `launch_executable` | `str` | Executable name (e.g., `codex`, `claude`, `gemini`) |
| `launch_defaults` | `LaunchDefaults` | Default launch arguments and tool parameters |
| `launch_metadata` | `ToolLaunchMetadata` | Metadata describing valid launch parameter definitions |
| `env_injection_mode` | `str` | How environment variables are injected at launch |
| `env_file_in_home` | `str \| None` | Path to an env file within the runtime home (if applicable) |
| `config_destination` | `str` | Relative path within the runtime home where config files are projected |
| `skills_destination` | `str` | Relative path within the runtime home where skill packages are projected |
| `skills_mode` | `str` | How skills are laid out in the destination |
| `credential_files_dir` | `str` | Directory within the runtime home for credential files |
| `credential_file_mappings` | `list[CredentialFileMapping]` | Rules mapping credential source files to their runtime home destinations |
| `credential_env_source` | `str` | Source location for credential environment variables |
| `credential_env_allowlist` | `list[str]` | Environment variable names allowed to pass through from credentials |

### Adapter Files

Tool adapters live in `brains/tool-adapters/<tool>.yaml` in the agent definition directory. Each supported tool requires exactly one adapter file that describes its filesystem and launch conventions.

## BlueprintBinding

A `BlueprintBinding` is a frozen dataclass that binds a brain recipe to a role, creating a complete agent configuration that can be built and launched in one step.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Blueprint name |
| `brain_recipe_path` | `Path` | Path to the brain recipe YAML file |
| `role` | `str` | Role name (resolved to `roles/<role>/system-prompt.md`) |
| `gateway` | `BlueprintGatewayDefaults \| None` | Optional gateway configuration defaults |

### Blueprint Files

Blueprints are YAML files stored under `blueprints/` in the agent definition directory. They provide a single declarative surface for specifying both the brain configuration (via a recipe reference) and the behavioral policy (via a role reference).
