## MODIFIED Requirements

### Requirement: Role injection documented per backend
The run-phase reference SHALL document how `plan_role_injection()` produces a `RoleInjectionPlan` with backend-specific strategies and SHALL explain why each backend uses its selected native surface.

The documented `RoleInjectionMethod` values SHALL match the code type and SHALL include the managed-home native system-prompt method used by Kimi 0.34.0 and later. The per-backend strategy table and Mermaid diagram SHALL map Kimi headless and local-interactive launches to native managed-home `SYSTEM.md` projection, and SHALL use `cao_profile` for the legacy `cao_rest` and `houmao_server_rest` backends.

The reference SHALL state that the complete effective launch prompt, not the raw role source alone, is projected before Kimi starts. It SHALL explain built-in prompt preservation, rejection of every `${identifier}` placeholder in Houmao prompt text, v2-engine enforcement, precedence conflicts, and manifest provenance.

#### Scenario: Reader understands why role injection differs by backend
- **WHEN** a reader opens the role-injection page
- **THEN** they find a table mapping each maintained backend to its injection method and provider surface
- **AND THEN** Kimi `>=0.34.0` maps to native managed-home system-prompt projection with no upper version limit

#### Scenario: Reader sees current RoleInjectionMethod values
- **WHEN** a reader checks the `RoleInjectionMethod` enumeration in the role-injection reference
- **THEN** the listed values match the implementation after native Kimi home-prompt support is added
- **AND THEN** neither `profile_based` nor an auto-skill injection method appears as current behavior

#### Scenario: Reader sees correct RoleInjectionMethod values
- **WHEN** a reader compares the role-injection reference with the current code type
- **THEN** every documented literal matches the current enumeration
- **AND THEN** the Kimi mapping names the native managed-home system-prompt method

### Requirement: Run-phase reference explains provider-native relaunch continuation
The run-phase reference SHALL document provider-native chat continuation during tmux-backed relaunch.

The session-lifecycle reference SHALL explain that relaunch reuses the managed session home and tmux window `0`, while the optional relaunch chat-session selector controls whether the provider starts fresh or resumes provider-native history.

The backend reference SHALL include provider-native startup mappings for every maintained local-interactive and native headless relaunch path. For Kimi 0.34.0 and later, it SHALL show `--auto` combined with `--continue` or `--session <session_id>` for unattended TUI relaunch, preserve `--model <alias>`, and explain that the native `SYSTEM.md` contract is validated before respawn.

The backend or launch reference SHALL document managed Kimi skill projection and `KIMI_CODE_NO_AUTO_UPDATE=1` accurately for each backend. Kimi role-injection guidance SHALL state that Houmao projects the complete role prompt natively before startup and SHALL contain no manual auto-skill or role-bootstrap instruction.

The launch-profile guide or linked run-phase documentation SHALL explain that launch-profile relaunch chat-session policy applies only to later relaunch of instances created from that profile and does not resume provider history on first launch.

#### Scenario: Reader understands TUI relaunch continuation
- **WHEN** a reader opens the run-phase session lifecycle or backend reference
- **THEN** the documentation explains that TUI relaunch continuation uses provider-native startup arguments before the TUI is respawned
- **AND THEN** it distinguishes that behavior from sending a resume request after startup

#### Scenario: Reader understands launch-profile relaunch policy scope
- **WHEN** a reader opens launch-profile or run-phase documentation for relaunch chat-session policy
- **THEN** the documentation states that the policy applies to later relaunch of instances created from the profile
- **AND THEN** first launch remains normal fresh provider startup

#### Scenario: Reader sees provider mapping table
- **WHEN** a reader needs to verify provider behavior for relaunch continuation
- **THEN** the backend reference includes native command forms for every maintained provider's TUI and headless continuation paths
- **AND THEN** unsupported provider/version combinations are not presented as compatible

#### Scenario: Reader sees Kimi-specific launch constraints
- **WHEN** a reader opens the Kimi Code local-interactive backend reference
- **THEN** it documents the `>=0.34.0` resume, auto-mode, model, update-suppression, and native prompt constraints
- **AND THEN** it states that role and policy chat bootstraps are absent

#### Scenario: Reader sees Kimi-specific relaunch and prompt constraints
- **WHEN** a reader opens the Kimi Code local-interactive backend reference
- **THEN** it documents native resume arguments, native auto mode, model selection, managed update suppression, and pre-start `SYSTEM.md` validation
- **AND THEN** it documents no post-readiness policy or role bootstrap command

### Requirement: Run-phase reference documents Kimi unattended TUI startup and relaunch
The run-phase backend and lifecycle references SHALL document that maintained Kimi Code 0.34.0-or-later local-interactive sessions can run with `operator_prompt_mode = unattended` while remaining visible TUI sessions.

The reference SHALL explain that unattended Kimi TUI startup uses native `--auto` after native managed-home role-prompt projection and that maintained Kimi 0.34.0-or-later behavior accepts this flag with `--continue` and `--session <session_id>`. It SHALL state that Houmao sends neither an auto-mode chat command nor a role-bootstrap chat turn.

The reference SHALL distinguish Kimi `as_is` TUI launch from unattended TUI launch, identify 0.34.0 as the minimum maintained version, state that Kimi releases before it are unsupported, and state that support has no upper version limit.

#### Scenario: Reader sees Kimi TUI unattended behavior
- **WHEN** a reader opens the Kimi local-interactive backend reference
- **THEN** it states that unattended startup includes native `--auto`
- **AND THEN** it states that native role instructions are in place before workload prompts

#### Scenario: Reader sees Kimi resumed startup behavior
- **WHEN** a reader opens the Kimi relaunch reference
- **THEN** it shows native `--auto` combined with `--continue` or `--session <session_id>`
- **AND THEN** it describes no post-readiness auto-mode or role-prompt command

#### Scenario: Reader can distinguish as-is from unattended
- **WHEN** a reader compares Kimi launch prompt modes
- **THEN** `as_is` preserves provider approval behavior
- **AND THEN** `unattended` is the maintained no-question mode without changing the native role-prompt method

#### Scenario: Reader sees current Kimi system-prompt evidence
- **WHEN** a reader opens the Kimi role-injection reference
- **THEN** the documentation describes the Kimi `>=0.34.0` native `SYSTEM.md` integration from current baseline source evidence
- **AND THEN** it presents no pre-0.34 compatibility path
