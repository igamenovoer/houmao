# Spec Delta

## ADDED Requirements

### Requirement: Provider start uses the resolved native launch settings

Managed provider start and explicit relaunch SHALL project the resolved native launch settings consistently into supported config files, CLI arguments, and native session parameters. Strategy writes SHALL preserve unrelated setup content. A managed service SHALL verify effective settings where its native handshake reports them before publishing readiness.

#### Scenario: A later native startup surface could override the managed configuration

- **WHEN** an operator sets a supported sandbox policy and the backend reads configuration before binding a native thread
- **THEN** the runtime applies the resolved sandbox policy through the backend's qualified startup surface
- **AND THEN** the config and native thread parameters agree where both define the setting

#### Scenario: A native session reports a different effective permission setting

- **WHEN** a native backend reports a permission setting different from the requested effective value during startup
- **THEN** the runtime reports the disagreement instead of publishing readiness for that configuration

#### Scenario: A relaunch reconstructs its permission settings

- **WHEN** a managed instance relaunches from saved authored inputs and an earlier runtime home contains generated permission defaults
- **THEN** provider start resolves the authored inputs and current applicable defaults for the selected executable
- **AND THEN** the prior materialized defaults do not shadow an explicit setting

## MODIFIED Requirements

### Requirement: Codex runtime launch applies non-interactive home bootstrap
For Codex launches, the runtime SHALL apply a runtime-owned bootstrap step to the generated Codex home configuration before starting the tool for:
- `backend=codex_headless`
- `backend=cao_rest`

Bootstrap behavior SHALL include:
- ensuring launch-context trust is recorded for the active workspace target in Codex project config, and
- seeding required notice state needed to avoid interactive onboarding/warning prompts for the selected policy profile, and
- applying the resolved non-secret launch preferences, including approval and sandbox settings from the authored inputs or the applicable launch-policy defaults.

#### Scenario: CAO Codex launch seeds trust for launch workspace
- **WHEN** a Codex CAO-backed session is started with a resolved working directory
- **THEN** runtime bootstrap writes/updates Codex runtime-home config so the launch workspace trust decision is pre-seeded before terminal start

#### Scenario: Codex headless launch uses the same bootstrap contract
- **WHEN** a Codex headless session is started from a generated brain home
- **THEN** runtime applies the same Codex bootstrap contract before the first headless CLI turn

### Requirement: Codex launch preferences use final CLI config overrides
For Houmao-managed Codex launches, the runtime SHALL pass Houmao-owned non-secret preferences as final Codex CLI config override arguments so those preferences take precedence over Codex config layers discovered from the launch working directory.

The runtime SHALL still preserve the same supported non-secret preferences in the generated Codex runtime home config when those preferences already have a runtime-home projection path.

At minimum, the Codex CLI override preference layer SHALL cover:

- resolved launch-owned model name,
- resolved launch-owned reasoning effort,
- resolved approval and sandbox settings, including versioned defaults for omitted unattended fields,
- selected model provider when Houmao owns provider selection for the launch,
- non-secret provider contract fields needed to prevent project-local provider config from changing a Houmao-owned provider selection.

The runtime SHALL NOT pass secret values such as API keys, auth JSON, OAuth tokens, cookies, or bearer tokens through CLI arguments.

#### Scenario: Project-local Codex reasoning config cannot override Houmao launch preference
- **WHEN** a Houmao-managed Codex launch resolves reasoning level `2` to `model_reasoning_effort = "low"`
- **AND WHEN** the generated Codex runtime home records `model_reasoning_effort = "low"`
- **AND WHEN** the launch working directory or one of its ancestors contains `.codex/config.toml` with `model_reasoning_effort = "high"`
- **THEN** the final Codex process arguments include a CLI config override for `model_reasoning_effort = "low"`
- **AND THEN** the live Codex session uses the Houmao-resolved reasoning preference

#### Scenario: Generated Codex home config remains as fallback state
- **WHEN** a Houmao-managed Codex launch resolves model `gpt-5.4` and reasoning effort `low`
- **THEN** the generated Codex runtime home config records those non-secret values when their runtime-home projection paths exist
- **AND THEN** the final Codex process arguments also include matching CLI config overrides for those Houmao-owned preferences
- **AND THEN** launches without a conflicting cwd/project Codex config still have readable generated-home fallback state

#### Scenario: Env-only provider selection is pinned without exposing secrets
- **WHEN** a Houmao-managed Codex launch selects an env-only provider configuration owned by the selected setup or launch profile
- **THEN** the final Codex process arguments include CLI config overrides for the non-secret selected provider name and required provider contract fields
- **AND THEN** the provider API key remains supplied through the existing env or auth-file mechanism
- **AND THEN** the API key value is not present in the process argument list

#### Scenario: Generated launch helper keeps explicit passthrough as manual override
- **WHEN** an operator manually invokes a generated Codex `launch.sh` helper with extra trailing Codex CLI config override args
- **THEN** those manually supplied trailing args remain later in the generated helper command than Houmao-generated preferences
- **AND THEN** normal managed launches that do not supply trailing passthrough args still use the Houmao-resolved preference layer

### Requirement: Runtime unattended launch can synthesize provider startup state from minimal credentials

When unattended launch is requested, the runtime SHALL start with the selected setup-projected runtime home. The selected strategy SHALL project authored native settings, fill omitted defaults, and synthesize its declared runtime-owned startup state before process start. This applies to every maintained backend that supports unattended launch.

Unattended compatibility SHALL be evaluated independently from credential readiness. The runtime SHALL provide the default unattended startup state without requiring pre-existing user-owned config or caller-supplied low-level arguments solely to suppress startup prompts.

#### Scenario: Fresh runtime home launches unattended from setup baseline plus strategy-owned overrides
- **WHEN** a session starts from a brain manifest that requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected tool setup projects a baseline `config.toml` into a fresh runtime home with a supported permission value
- **THEN** the runtime copies the setup baseline and applies the authored value
- **AND THEN** the selected strategy fills missing permission defaults and synthesizes required startup state

#### Scenario: Missing credential fails readiness without redefining unattended compatibility
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** a compatible unattended strategy exists for the detected tool version and backend
- **AND WHEN** the resolved provider lacks required secret material
- **THEN** the runtime fails before provider start with a credential-readiness error

#### Scenario: Claude unattended launch follows the same authoritative contract
- **WHEN** a Claude Code session requests `operator_prompt_mode = unattended` with minimal credentials and no authored permission value
- **THEN** the strategy synthesizes its qualified permission defaults and required startup state
- **AND THEN** startup needs no user-prepared Claude settings or permission flags

### Requirement: Strategy-owned launch args are not silently overridden

The selected strategy SHALL emit managed launch arguments from resolved native values and backend-derived controls. It SHALL validate equivalent dedicated flags and generic config overrides so recognized configurable values retain their precedence and attempts to set reserved controls fail explicitly.

#### Scenario: Conflicting launch override is canonicalized to the unattended strategy
- **WHEN** a session requests `operator_prompt_mode = unattended` and supplies a supported permission override through a recognized native launch input
- **AND WHEN** that value differs from the unattended default
- **THEN** launch uses the resolved override instead of the omitted-field default
- **AND THEN** the strategy projects a consistent native representation

#### Scenario: Conflicting Codex config-override arg is canonicalized to the unattended strategy
- **WHEN** the caller submits a generic native config override for a field that the backend reserves
- **THEN** the runtime identifies the canonical reserved field and rejects it before starting or replacing the provider

### Requirement: Runtime resolves the effective launch overrides for the selected backend before provider start

The system SHALL resolve effective launch settings during launch-plan composition using the brain manifest, selected backend, and detected tool version.

The runtime SHALL resolve the authored argument and tool-parameter layers with their documented precedence, validate supported settings and reserved protocol controls, and apply default values only to the remaining omissions. Provider startup SHALL use the resulting arguments, home projection, and derived continuity controls.

#### Scenario: Runtime resolves a Claude headless launch override with a supported typed param
- **WHEN** a Claude brain manifest contains an effective `tool_params.include_partial_messages` value of true
- **AND WHEN** the selected backend is `claude_headless`
- **THEN** launch-plan composition enables partial messages before provider start
- **AND THEN** the launch plan preserves runtime-owned continuity and machine-readable output controls

### Requirement: Kimi unattended local-interactive launch runs in automatic no-question mode

A maintained Kimi TUI launch SHALL apply the resolved permission mode using qualified native startup inputs before a managed prompt. The unattended default SHALL be `auto` where the operator omits a permission mode. The native startup path SHALL preserve a supported explicit mode and keep policy setup outside the conversation. An `as_is` launch with an omitted permission mode SHALL retain native session behavior.

#### Scenario: Fresh unattended Kimi TUI launch starts in auto mode
- **WHEN** a managed Kimi TUI launches with unattended defaults and the author omits permission mode
- **THEN** the runtime projects `default_permission_mode = "auto"` and uses native `--auto` at launch
- **AND THEN** native role instructions are in place before the first workload prompt

#### Scenario: Resumed unattended Kimi TUI launch refreshes auto mode
- **WHEN** an unattended Kimi TUI relaunch resumes history with `--continue` or `--session <session_id>` and permission mode is omitted
- **THEN** the startup command includes the native `--auto` option with the continuation selector
- **AND THEN** the first managed conversational input can be workload content

#### Scenario: Unsupported Kimi permission selection fails before launch
- **WHEN** the Kimi TUI cannot establish the authored permission mode using the selected native startup path
- **THEN** Houmao reports the unsupported setting and startup combination before starting the provider

#### Scenario: Auto refresh failure blocks unattended launch
- **WHEN** an unattended launch needs the Kimi auto default and the native startup path cannot establish it
- **THEN** Houmao reports the unsupported startup combination before admitting workload prompts

#### Scenario: As-is Kimi TUI remains manual when provider chooses manual
- **WHEN** a Kimi TUI launches in `as_is` with permission mode omitted
- **AND WHEN** the provider's selected native settings or session choose manual mode
- **THEN** the provider determines the permission mode from its selected native settings and session

#### Scenario: Kimi auto mode is no-question but not hard-deny bypass
- **WHEN** a Kimi TUI starts in the unattended default auto mode
- **THEN** ordinary tool approvals and user questions do not require operator input
- **AND THEN** native hard denials and explicit deny rules still apply

### Requirement: Web Human Interaction Follows the Selected Operator Policy

DSH Web SHALL use the resolved sandbox, approval, and model configuration. Omitted permission settings SHALL use native defaults for `as_is` and the qualified unattended defaults for `unattended`. An explicit approval policy SHALL control human participation. Browser opening SHALL be explicit and public launch or status data SHALL omit sign-in credentials.

#### Scenario: Human Operates an As-Is DSH Session
- **WHEN** a DSH Web session uses `as_is` and its effective policy requests human approval
- **THEN** the browser presents the interaction while Houmao observes the blocked state
- **AND THEN** observation or reconnect preserves the effective native policy

#### Scenario: Authored approval overrides the unattended Web default
- **WHEN** a DSH Web launch requests `unattended` and explicitly sets approval to `ask`
- **THEN** the session uses the selected approval setting and presents native approval requests through the browser

#### Scenario: Automated Web Qualification Has No Display
- **WHEN** an unattended DSH Web fixture launches without a graphical desktop
- **THEN** the host becomes controllable and the browser can connect separately to the same native session

### Requirement: Unattended DSH Launch Composes Coherent Permission Presets

DSH headless, ACP service, and Web SHALL resolve sandbox and approval independently for each launch. Unattended defaults SHALL be `danger-full-access` and `never`. Profile generation SHALL select a native permission preset consistent with the effective sandbox and approval sections, preserving supported explicit settings and omitting unattended defaults for `as_is`.

#### Scenario: Unattended Launch Activates Native Permission Service Cleanly
- **WHEN** a managed DSH backend starts with unattended mode and both permission fields omitted
- **THEN** the generated profile selects a preset with `danger-full-access` and `never` matching the native sandbox and approval sections
- **AND THEN** DSH activates its native permission service without a preset-mismatch error

#### Scenario: One authored field changes the selected preset
- **WHEN** a managed unattended DSH launch sets sandbox to `workspace-write` and leaves approval unset
- **THEN** the profile selects a preset with `workspace-write` and the `never` default
- **AND THEN** the native sandbox and approval sections agree with that preset

#### Scenario: As-Is Launch Preserves Native Permission Defaults
- **WHEN** a managed DSH backend starts in `as_is` without permission overrides
- **THEN** the native profile uses its existing baseline permissions
- **AND THEN** Houmao projects no unattended permission defaults

## REMOVED Requirements

### Requirement: Unattended runtime-owned config overrides replace conflicting setup values in the runtime home

**Reason**: The requirement treated authored permission settings as disposable and prescribed behavior for a retired backend.

**Migration**: Use the resolved-setting projection contract. Supply supported permission fields through the selected native setup or `tool_params`, and omit reserved runtime controls.

### Requirement: Unattended runtime-owned launch surfaces replace conflicting caller launch inputs

**Reason**: The requirement made forced permission flags override authored values.

**Migration**: Use a supported typed tool parameter or native launch input for configurable fields. Use Houmao's managed launch and continuation selectors for reserved controls.
