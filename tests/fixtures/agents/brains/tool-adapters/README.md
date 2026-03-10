# Tool Adapter Schema

Each adapter file (`<tool>.yaml`) declares how the builder projects config, skills, credentials, and launch settings into a runtime home.

Schema (`schema_version: 1`):

- `tool`: tool identifier (`codex`, `claude`, `gemini`)
- `home_selector.env_var`: environment variable used to point the CLI at a constructed home
- `launch.executable`: CLI executable name
- `launch.args`: default launch args
- `launch.env_injection.mode`:
  - `home_dotenv`: tool reads env vars from a dotenv file inside the home
  - `export_from_env_file`: launcher exports allowlisted vars from credential env file
- `launch.env_injection.env_file_in_home`: required when mode is `home_dotenv`
- `config_projection.destination`: destination directory inside runtime home
- `skills_projection.destination`: destination directory for selected skills
- `skills_projection.mode`: `symlink` or `copy`
- `credential_projection.files_dir`: credential files directory under a credential profile
- `credential_projection.file_mappings[]`: `{source, destination, mode, required?}`
  - `required` defaults to `true`
  - mappings with `required: false` are skipped when the source file is absent
- `credential_projection.env.source`: path to credential env file under a credential profile
- `credential_projection.env.allowlist[]`: env vars allowed for launch injection

Claude headless note:

- `launch.args` defines the base Claude CLI flags (for example `-p` and/or `--dangerously-skip-permissions`).
- Backend-reserved args are injected by runtime code and must not appear in `launch.args`:
  - `--resume`
  - `--output-format`
  - `--append-system-prompt`
