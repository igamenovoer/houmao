# Spec Delta

## MODIFIED Requirements

### Requirement: Codex runtime launch applies non-interactive home bootstrap
For Codex launches, the runtime SHALL apply a runtime-owned bootstrap step to the generated Codex home configuration before starting the tool for:
- `backend=codex_headless`
- `backend=cao_rest`

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Bootstrap behavior SHALL include:
- ensuring launch-context trust is recorded for the active workspace target in Codex project config, and
- seeding required notice state needed to avoid interactive onboarding/warning prompts for the selected policy profile, and
- applying the resolved non-secret launch preferences, including the qualified approval and sandbox settings selected by the unattended policy, or supported authored values and the native baseline under `as_is`.

#### Scenario: CAO Codex launch seeds trust for launch workspace
- **WHEN** a Codex CAO-backed session is started with a resolved working directory
- **THEN** runtime bootstrap writes/updates Codex runtime-home config so the launch workspace trust decision is pre-seeded before terminal start

#### Scenario: Codex headless launch uses the same bootstrap contract
- **WHEN** a Codex headless session is started from a generated brain home
- **THEN** runtime applies the same Codex bootstrap contract before the first headless CLI turn

### Requirement: Runtime unattended launch can synthesize provider startup state from minimal credentials

When unattended launch is requested, the runtime SHALL start with the selected setup-projected runtime home. The selected strategy SHALL establish the qualified maximum unattended permission posture and synthesize its declared runtime-owned startup state before process start. Other supported authored native settings SHALL retain their documented precedence. This applies to every maintained backend that supports unattended launch.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Unattended compatibility SHALL be evaluated independently from credential readiness. The runtime SHALL provide the default unattended startup state without requiring pre-existing user-owned config or caller-supplied low-level arguments solely to suppress startup prompts.

#### Scenario: Fresh runtime home launches unattended from setup baseline plus strategy-owned overrides
- **WHEN** a session starts from a brain manifest that requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected tool setup supplies a baseline `config.toml` with a matching effective permission value
- **THEN** the runtime copies the setup baseline into the fresh runtime home
- **AND THEN** the selected strategy projects the complete qualified permission posture and synthesizes required startup state

#### Scenario: Missing credential fails readiness without redefining unattended compatibility
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** a compatible unattended strategy exists for the detected tool version and backend
- **AND WHEN** the resolved provider lacks required secret material
- **THEN** the runtime fails before provider start with a credential-readiness error

#### Scenario: Claude unattended launch follows the same authoritative contract
- **WHEN** a Claude Code session requests `operator_prompt_mode = unattended` with minimal credentials and no authored permission value
- **THEN** the strategy establishes `bypassPermissions` and synthesizes required startup state
- **AND THEN** startup needs no user-prepared Claude settings or permission flags

### Requirement: Strategy-owned launch args are not silently overridden

The selected strategy SHALL emit managed launch arguments from resolved native values and backend-derived controls. It SHALL normalize equivalent dedicated flags and generic config overrides with the documented precedence. It SHALL reject effective permission values that conflict with unattended posture and attempts to set reserved controls.

#### Scenario: Conflicting launch override is canonicalized to the unattended strategy
- **WHEN** a session requests `operator_prompt_mode = unattended` and supplies a supported permission override through a recognized native launch input
- **AND WHEN** that value matches the qualified unattended posture after normalization
- **THEN** the strategy projects one consistent native representation
- **AND THEN** an equivalent alias adds no competing provider argument

#### Scenario: Conflicting Codex config-override arg is canonicalized to the unattended strategy
- **WHEN** the caller submits a generic native config override for a field that the backend reserves
- **THEN** the runtime identifies the canonical reserved field and rejects it before starting or replacing the provider

#### Scenario: Conflicting effective permission blocks provider start

- **WHEN** a fresh start or explicit relaunch in `unattended` resolves an effective authored permission value that differs from the qualified native value
- **THEN** validation identifies the effective field, source, and required value and directs the operator to `as_is` for custom permissions
- **AND THEN** validation fails before modifying an existing runtime home, stopping or replacing the current provider, or publishing a new binding

### Requirement: Runtime resolves the effective launch overrides for the selected backend before provider start

The runtime SHALL resolve effective launch settings before provider start using the brain manifest, backend, and tool version. It SHALL validate authored argument and tool-parameter layers, including reserved controls. Unattended approval and sandbox values SHALL follow the qualified permission policy. Other fields SHALL retain their documented precedence and omission rules. Startup SHALL use the resulting arguments, native home projection, and derived continuity controls.

#### Scenario: Runtime resolves a Claude headless launch override with a supported typed param
- **WHEN** a Claude brain manifest contains an effective `tool_params.include_partial_messages` value of true
- **AND WHEN** the selected backend is `claude_headless`
- **THEN** launch-plan composition enables partial messages before provider start
- **AND THEN** the launch plan preserves runtime-owned continuity and machine-readable output controls

#### Scenario: A setup permission is superseded by a matching winning value

- **WHEN** an unattended launch resolves a recognized native setup permission, a typed setup override, and a higher authored layer for the same field
- **AND WHEN** the highest-precedence normalized value matches the selected unattended posture
- **THEN** launch uses the qualified native permission posture
- **AND THEN** lower-priority valid settings cannot reach the final native arguments, config, or start request

#### Scenario: An unattended launch uses a retained authored snapshot

- **WHEN** provider start reads a saved definition or launch snapshot with a valid but conflicting effective permission setting
- **THEN** launch reports the conflict before changing an existing runtime or starting the provider
- **AND THEN** validation preserves the stored authored input

### Requirement: Codex launch preferences use final CLI config overrides
For Houmao-managed Codex launches, the runtime SHALL pass Houmao-owned non-secret preferences as final Codex CLI config override arguments so those preferences take precedence over Codex config layers discovered from the launch working directory.

The runtime SHALL still preserve the same supported non-secret preferences in the generated Codex runtime home config when those preferences already have a runtime-home projection path.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

At minimum, the Codex CLI override preference layer SHALL cover:

- resolved launch-owned model name,
- resolved launch-owned reasoning effort,
- resolved approval and sandbox settings, including the qualified maximum unattended posture,
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
- **WHEN** an operator invokes a generated Codex `launch.sh` helper in `as_is` with supported trailing Codex CLI config override arguments
- **THEN** the supported manual overrides remain effective under that launch mode
- **AND THEN** managed launches without trailing passthrough arguments use the Houmao-resolved preference layer

#### Scenario: Generated unattended helper validates trailing permission options

- **WHEN** an operator invokes a Houmao-generated provider-start helper in `unattended` with a trailing native option for approval, sandbox, or permission mode
- **THEN** the option participates in permission normalization and validation before provider start
- **AND THEN** a conflicting effective setting fails before provider-start mutation
- **AND THEN** a matching effective option cannot change the native unattended posture
- **AND THEN** unrelated supported passthrough arguments remain available

### Requirement: Kimi unattended local-interactive launch runs in automatic no-question mode

A maintained Kimi TUI launch SHALL apply the resolved permission mode using qualified native startup inputs before a managed prompt. Unattended startup SHALL establish `auto` and reject a conflicting effective authored mode. Under `as_is`, the native startup path SHALL apply a supported explicit mode and use native session behavior for an omitted mode. Policy setup SHALL occur outside the conversation.

#### Scenario: Fresh unattended Kimi TUI launch starts in auto mode
- **WHEN** a managed Kimi TUI launches unattended with an omitted or matching effective permission setting
- **THEN** the runtime projects `default_permission_mode = "auto"` and uses native `--auto` at launch
- **AND THEN** native role instructions are in place before the first workload prompt

#### Scenario: Resumed unattended Kimi TUI launch refreshes auto mode
- **WHEN** an unattended Kimi TUI relaunch resumes history with `--continue` or `--session <session_id>`
- **THEN** the startup command includes the native `--auto` option with the continuation selector
- **AND THEN** the first managed conversational input can be workload content

#### Scenario: Unsupported Kimi permission selection fails before launch
- **WHEN** the selected native startup path cannot establish an effective authored `as_is` permission mode
- **THEN** Houmao reports the unsupported setting and startup combination before starting the provider

#### Scenario: Auto refresh failure blocks unattended launch
- **WHEN** an unattended launch cannot establish the required Kimi `auto` posture
- **THEN** Houmao reports the unsupported startup combination before admitting workload prompts

#### Scenario: As-is Kimi TUI remains manual when provider chooses manual
- **WHEN** a Kimi TUI launches in `as_is` with permission mode omitted
- **AND WHEN** the provider's selected native settings or session choose manual mode
- **THEN** the provider determines the permission mode from its selected native settings and session

#### Scenario: Kimi auto mode is no-question but not hard-deny bypass
- **WHEN** a Kimi TUI starts in unattended `auto` mode
- **THEN** ordinary tool approvals and user questions do not require operator input
- **AND THEN** native hard denials and explicit deny rules still apply

#### Scenario: Kimi unattended TUI rejects an effective manual or yolo setting

- **WHEN** a Kimi TUI starts or explicitly relaunches unattended with an effective `manual` or `yolo` setting
- **THEN** launch reports `auto` as the required unattended posture before mutating provider-start state

### Requirement: Web Human Interaction Follows the Selected Operator Policy

DSH Web SHALL use the resolved sandbox, approval, and model configuration. `unattended` SHALL require the qualified native sandbox and approval posture. `as_is` SHALL apply supported explicit settings and use the native baseline for omissions. Under `as_is`, the effective approval policy SHALL control human participation. Browser opening SHALL be explicit and public launch or status data SHALL omit sign-in credentials.

#### Scenario: Human Operates an As-Is DSH Session
- **WHEN** a DSH Web session uses `as_is` and its effective policy requests human approval
- **THEN** the browser presents the interaction while Houmao observes the blocked state
- **AND THEN** observation or reconnect preserves the effective native policy

#### Scenario: Authored approval overrides the unattended Web default
- **WHEN** an operator changes a DSH Web launch from `unattended` to `as_is` and explicitly sets approval to `ask`
- **THEN** the new session uses the selected approval setting and presents native approval requests through the browser

#### Scenario: Automated Web Qualification Has No Display
- **WHEN** an unattended DSH Web fixture launches without a graphical desktop
- **THEN** the host becomes controllable and the browser can connect separately to the same native session

#### Scenario: Unattended DSH Web rejects an authored approval wait

- **WHEN** a DSH Web launch requests `unattended` and resolves an effective `ask` approval value
- **THEN** launch reports `never` as the required unattended approval value before starting or replacing the Web host

### Requirement: Unattended DSH Launch Composes Coherent Permission Presets

DSH headless, ACP service, and Web SHALL use `danger-full-access` and `never` in unattended mode and reject a conflicting effective value for either field. Profile generation SHALL select a native preset consistent with the effective sandbox and approval sections. `as_is` SHALL honor supported explicit settings and use the native baseline for omissions.

#### Scenario: Unattended Launch Activates Native Permission Service Cleanly
- **WHEN** a managed DSH backend starts in unattended mode with omitted or matching effective permission inputs
- **THEN** the generated profile selects a preset with `danger-full-access` and `never` matching the native sandbox and approval sections
- **AND THEN** DSH activates its native permission service without a preset-mismatch error

#### Scenario: One authored field changes the selected preset
- **WHEN** a managed DSH launch in `as_is` sets sandbox to `read-only` and leaves approval unset
- **THEN** the profile selects a preset with `read-only` and the native baseline approval
- **AND THEN** the native sandbox and approval sections agree with that preset

#### Scenario: As-Is Launch Preserves Native Permission Defaults
- **WHEN** a managed DSH backend starts in `as_is` without permission overrides
- **THEN** the native profile uses its existing baseline permissions
- **AND THEN** Houmao projects no unattended permission defaults

#### Scenario: A partial DSH permission tuple conflicts with unattended launch

- **WHEN** a managed unattended DSH launch supplies an effective `workspace-write` sandbox and leaves approval unset
- **THEN** launch identifies the sandbox conflict before projecting the native permission preset or starting a provider

### Requirement: Provider start uses the resolved native launch settings

Managed provider start and explicit relaunch SHALL project the resolved native launch settings consistently into supported config files, CLI arguments, and native session parameters. Strategy writes SHALL preserve unrelated setup content. A managed service SHALL verify effective settings where its native handshake reports them before publishing readiness.

#### Scenario: A later native startup surface could override the managed configuration

- **WHEN** a backend reads configuration before binding a native thread under unattended policy or an effective supported `as_is` sandbox setting
- **THEN** the runtime applies the resolved sandbox policy through the backend's qualified startup surface
- **AND THEN** the config and native thread parameters agree where both define the setting

#### Scenario: A native session reports a different effective permission setting

- **WHEN** a native backend reports a permission setting different from the requested effective value during startup
- **THEN** the runtime reports the disagreement instead of publishing readiness for that configuration

#### Scenario: Native binding cannot establish the required unattended mode after static validation

- **WHEN** launch passes authored-setting and known compatibility checks but the newly bound native provider lacks a required unattended capability or cannot establish its effective permission posture
- **THEN** startup reports the failed native check and withholds readiness
- **AND THEN** startup rolls back its owned effects using the scoped startup boundary while preserving existing data and unrelated runtimes

#### Scenario: A relaunch reconstructs its permission settings

- **WHEN** a managed instance relaunches from saved authored inputs and an earlier runtime home contains generated permission defaults
- **THEN** provider start resolves the stored authored inputs and the current qualified policy for the selected executable
- **AND THEN** a previously generated permission value does not count as authored input or shadow the policy selected for this launch

#### Scenario: A relaunch rejects newly conflicting saved intent

- **WHEN** a saved authored permission value that a prior release accepted conflicts with the current unattended posture
- **THEN** explicit relaunch reports the conflict before changing the runtime home or stopping the existing native provider
- **AND THEN** it preserves the current runtime binding, history, and authored snapshot
