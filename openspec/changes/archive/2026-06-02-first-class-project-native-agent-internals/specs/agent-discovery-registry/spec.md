## MODIFIED Requirements

### Requirement: Shared agent registry uses a fixed per-user root with isolated live-agent directories
The shared agent registry SHALL keep its fixed per-user root under the platformdirs user config path for app name `houmao` and no app author, and SHALL support an env-var override named `HOUMAO_GLOBAL_REGISTRY_DIR`.

On Linux, the default shared registry root is expected to be `~/.config/houmao/registry`.

When `HOUMAO_GLOBAL_REGISTRY_DIR` is set to an absolute directory path, the system SHALL use that value as the effective registry root instead of the platformdirs-derived default. The override SHALL support CI, tests, and similarly controlled environments.

#### Scenario: Env-var override relocates the shared registry root
- **WHEN** `HOUMAO_GLOBAL_REGISTRY_DIR` is set to an absolute directory path
- **THEN** the system uses that directory as the effective shared registry root

#### Scenario: Default registry root uses platformdirs config path
- **WHEN** `HOUMAO_GLOBAL_REGISTRY_DIR` is unset
- **THEN** the system derives the effective shared registry root from the platformdirs user config path for `houmao`
- **AND THEN** on ordinary Linux systems the path is `~/.config/houmao/registry`
- **AND THEN** the default is not `~/.houmao/registry`
