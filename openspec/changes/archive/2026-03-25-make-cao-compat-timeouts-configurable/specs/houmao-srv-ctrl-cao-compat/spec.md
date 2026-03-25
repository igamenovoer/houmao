## ADDED Requirements

### Requirement: Session-backed compatibility launch exposes additive timeout override controls
Session-backed pair launch SHALL expose additive operator controls for the CAO-compatible client timeout budgets used during compatibility launch.

At minimum, the session-backed launch surfaces SHALL accept:

- `--compat-http-timeout-seconds`
- `--compat-create-timeout-seconds`

When those flags are omitted, the session-backed launch surfaces SHALL resolve defaults from these optional environment variables before falling back to built-in client defaults:

- `HOUMAO_COMPAT_HTTP_TIMEOUT_SECONDS`
- `HOUMAO_COMPAT_CREATE_TIMEOUT_SECONDS`

CLI flags SHALL take precedence over environment-variable defaults.

This requirement SHALL apply to:

- `houmao-mgr cao launch`
- top-level `houmao-mgr launch` when it is using the session-backed TUI compatibility path

These additive timeout controls SHALL affect only the CAO-compatible pair client used for session-backed launch. They SHALL NOT redefine the native headless launch contract.

#### Scenario: Namespaced compatibility launch accepts additive timeout overrides
- **WHEN** an operator runs `houmao-mgr cao launch --compat-create-timeout-seconds 90 ...`
- **THEN** `houmao-mgr` uses a 90-second create-operation timeout budget for the compatibility session-creation request
- **AND THEN** the command remains valid without requiring any Houmao-only timeout flag for ordinary compatibility usage

#### Scenario: Environment default applies when explicit timeout flags are omitted
- **WHEN** an operator sets `HOUMAO_COMPAT_HTTP_TIMEOUT_SECONDS` and `HOUMAO_COMPAT_CREATE_TIMEOUT_SECONDS`
- **AND WHEN** the operator runs a session-backed compatibility launch without the corresponding flags
- **THEN** `houmao-mgr` uses those environment-provided timeout budgets for the compatibility client
- **AND THEN** an explicit flag would override the environment value if later provided

#### Scenario: Native headless launch rejects compatibility-only timeout flags
- **WHEN** an operator runs top-level `houmao-mgr launch --headless` and also supplies `--compat-http-timeout-seconds` or `--compat-create-timeout-seconds`
- **THEN** the command fails explicitly
- **AND THEN** it does not imply that native headless launch honors CAO-compatible timeout controls
