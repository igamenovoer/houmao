## Purpose
Define the historical CAO-compatibility capability state for `houmao-mgr`.

## Requirements

This capability has no active requirements after retirement of the `cao` namespace and top-level `launch` compatibility surface.

Houmao-owned CLI behavior SHALL be tested directly and more strictly. That verification SHALL cover at minimum:

- native headless top-level `launch --headless`
- session-backed top-level `launch` registration and runtime artifact materialization
- namespaced compatibility launch/info/shutdown through the pair
- native selector resolution for both headless and session-backed launch, including brain-only empty-prompt behavior

#### Scenario: Compatibility verification catches namespace regressions
- **WHEN** a `houmao-mgr cao` command changes in a way that breaks CAO-compatible invocation shape or compatibility-significant behavior
- **THEN** compatibility verification detects the divergence
- **AND THEN** the implementation can reject that change before claiming namespaced CAO compatibility

#### Scenario: Houmao-owned verification catches pair-command regressions
- **WHEN** a top-level or namespaced Houmao-owned command changes in a way that breaks pair launch, native selector resolution, or compatibility-wrapper behavior
- **THEN** direct Houmao behavior verification detects the regression
- **AND THEN** the implementation can reject that change even though no external `cao` subprocess is involved

### Requirement: Delegated launch preserves authoritative tmux window identity
When `houmao-mgr launch` completes successfully inside the supported pair, it SHALL recover tmux window identity from the pair authority's session-detail response and SHALL persist that window identity into Houmao-owned registration and runtime artifacts whenever the metadata is available.

This preservation SHALL use the authoritative session-detail response rather than deriving tmux window identity from `terminal_id` or another unrelated field.

#### Scenario: Launch registration preserves tmux window identity from session detail
- **WHEN** `houmao-mgr launch` receives a successful session-detail response whose terminal summary includes tmux window metadata
- **THEN** `houmao-mgr` includes that tmux window identity in the registration payload sent to `houmao-server`
- **AND THEN** the corresponding Houmao-owned runtime artifacts persist the same window identity for later tracking and resume flows

#### Scenario: Missing tmux window metadata does not fabricate a value
- **WHEN** a successful delegated launch does not expose tmux window metadata in the session-detail response
- **THEN** `houmao-mgr` leaves that field unset in its Houmao-owned follow-up artifacts
- **AND THEN** the CLI does not invent a replacement value from `terminal_id` or another incompatible field

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
