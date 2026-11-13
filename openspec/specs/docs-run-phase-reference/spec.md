# docs-run-phase-reference Specification

## Purpose
Define the documentation requirements for Houmao run-phase reference content.
## Requirements

### Requirement: LaunchPlan composition documented

The run-phase reference SHALL include a page documenting `LaunchPlan` composition: how `build_launch_plan()` takes a `LaunchPlanRequest` (brain_manifest + role_package + backend + working_directory) and produces a `LaunchPlan` with backend-specific launch arguments. Content SHALL be derived from `launch_plan.py` docstrings.

The page SHALL state that the brain manifest carries launch-profile-derived inputs into runtime launch resolution when the launch originated from a reusable launch profile, including:

- effective auth selection,
- operator prompt-mode intent,
- durable non-secret env records,
- declarative mailbox configuration,
- managed-agent identity defaults,
- prompt-overlay-composed effective role prompt.

The page SHALL state that the build manifest and runtime launch metadata preserve secret-free launch-profile provenance sufficient for inspection and replay, including whether the birth-time config came from an project profile or an explicit launch profile, and the originating profile name when available.

The page SHALL state that runtime `LaunchPlan` is derived and ephemeral and SHALL NOT be presented as a user-authored object.

The page SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model that ties launch profiles to the run-phase composition pipeline.

#### Scenario: Reader understands launch plan resolution

- **WHEN** a reader opens the launch-plan page
- **THEN** they find the `LaunchPlanRequest` fields, the resolution logic (env vars, launch overrides, mailbox bindings, role injection), and the resulting `LaunchPlan` structure

#### Scenario: Reader understands how launch-profile inputs flow into runtime launch resolution

- **WHEN** a reader opens the launch-plan page and looks at how a launch-profile-backed launch is resolved
- **THEN** the page explains that auth selection, operator prompt-mode intent, durable env records, declarative mailbox configuration, managed-agent identity defaults, and the prompt-overlay-composed effective role prompt come through the manifest from the originating launch profile
- **AND THEN** the page explains that launch-profile provenance is preserved in secret-free form on the build manifest and runtime launch metadata

### Requirement: Session lifecycle documented

The run-phase reference SHALL include a page documenting `RuntimeSessionController` and the session lifecycle using the current `start_runtime_session()` and `resume_runtime_session()` behavior derived from `runtime.py`.

That page SHALL describe:

- current start and resume inputs at the level needed for reader understanding,
- session manifest persistence under the runtime-owned session root,
- the distinction between the runtime-owned session root and the workspace-local `job_dir`,
- current lifecycle actions such as prompt delivery, interrupt, raw control input when supported, and stop behavior.

#### Scenario: Reader understands session-root versus job-dir state

- **WHEN** a reader opens the session-lifecycle page
- **THEN** they find that the persisted session manifest lives under the runtime-owned session root
- **AND THEN** the page explains that the workspace-local `job_dir` is a separate per-session scratch or output location rather than the root of authoritative runtime state

#### Scenario: Reader sees current lifecycle behavior rather than stale signatures

- **WHEN** a reader uses the session-lifecycle page to understand start and resume behavior
- **THEN** the page reflects the current runtime lifecycle surfaces and current persistence model
- **AND THEN** it does not describe outdated function signatures or job-dir manifest placement as the current implementation

#### Scenario: Reader understands degraded and stale recovery in the lifecycle diagram

- **WHEN** a reader opens the session-lifecycle page and views the lifecycle diagram
- **THEN** the diagram or accompanying text indicates that `stop` and `relaunch` may route through recovery when the tmux session is degraded or stale

### Requirement: Session lifecycle includes degraded and stale recovery paths

The session-lifecycle reference page SHALL include a subsection covering degraded and stale recovery as a first-class lifecycle path. The subsection SHALL state that when a registry record claims `active` but tmux inspection reveals a broken session, `agents stop` and `agents relaunch` route through dedicated recovery helpers instead of failing with a generic unusable-target error. The subsection SHALL link to the dedicated degraded-stale recovery reference page.

#### Scenario: Reader discovers recovery from session-lifecycle page

- **WHEN** a reader reads the session-lifecycle page
- **THEN** they see recovery mentioned alongside start, resume, prompt, and stop
- **AND THEN** they can follow a link to the dedicated recovery page for full details

### Requirement: Backend model documented with per-backend notes

The run-phase reference SHALL include a page documenting the `BackendKind` type and each backend implementation with the current public posture: `local_interactive` as primary, native headless backends as direct CLI alternatives, and `cao_rest` plus `houmao_server_rest` as legacy or compatibility paths. Content SHALL be derived from `models.py` and per-backend module docstrings.

The backend reference SHALL explicitly distinguish between implemented backend existence and recommended operator usage.

When the launch policy reference mentions launch surfaces, it SHALL clarify the relationship between `LaunchSurface` (build-phase type that includes `raw_launch`) and `BackendKind` (run-phase type that uses `local_interactive`). The docs SHALL note that `raw_launch` in the build-phase surface maps to `local_interactive` at runtime.

#### Scenario: local_interactive presented as primary

- **WHEN** a reader opens the backends page
- **THEN** `local_interactive` is the first and most detailed backend described, with headless backends next, and CAO-backed backends last with a "legacy" label

#### Scenario: Legacy backends reflect current operator posture

- **WHEN** the backends page describes `cao_rest` and `houmao_server_rest`
- **THEN** it makes clear that standalone `cao_rest` operator workflows are retired and that those backends remain legacy or compatibility-oriented runtime paths
- **AND THEN** the page does not describe them as the primary recommended backend choice for new operator workflows

#### Scenario: Backend selection logic explained

- **WHEN** the backends page describes backend resolution
- **THEN** it explains `backend_for_tool()` mapping and how `LaunchPlan.backend` is determined

#### Scenario: Launch surface vs backend kind distinction clarified

- **WHEN** a reader checks the launch policy reference for backend surface examples
- **THEN** the page explains that `LaunchSurface` includes `raw_launch` while `BackendKind` uses `local_interactive`
- **AND THEN** the page notes that `raw_launch` maps to `local_interactive` at runtime

### Requirement: Role injection documented per backend
The run-phase reference SHALL document how `plan_role_injection()` produces a `RoleInjectionPlan` with backend-specific strategies and SHALL explain why each backend uses its selected native surface.

The documented `RoleInjectionMethod` values SHALL match the code type and SHALL include the managed-home native system-prompt method used by Kimi 2.1.1 and later. The per-backend strategy table and Mermaid diagram SHALL map Kimi headless and local-interactive launches to native managed-home `SYSTEM.md` projection, and SHALL use `cao_profile` for the legacy `cao_rest` and `houmao_server_rest` backends.

The reference SHALL state that the complete effective launch prompt, not the raw role source alone, is projected before Kimi starts. It SHALL explain built-in prompt preservation, rejection of every `${identifier}` placeholder in Houmao prompt text, v2-engine enforcement, precedence conflicts, and manifest provenance.

#### Scenario: Reader understands why role injection differs by backend
- **WHEN** a reader opens the role-injection page
- **THEN** they find a table mapping each maintained backend to its injection method and provider surface
- **AND THEN** Kimi `>=2.1.1` maps to native managed-home system-prompt projection with no upper version limit

#### Scenario: Reader sees current RoleInjectionMethod values
- **WHEN** a reader checks the `RoleInjectionMethod` enumeration in the role-injection reference
- **THEN** the listed values match the implementation after native Kimi home-prompt support is added
- **AND THEN** neither `profile_based` nor an auto-skill injection method appears as current behavior

#### Scenario: Reader sees correct RoleInjectionMethod values
- **WHEN** a reader compares the role-injection reference with the current code type
- **THEN** every documented literal matches the current enumeration
- **AND THEN** the Kimi mapping names the native managed-home system-prompt method

### Requirement: Legacy backend documentation carries an unmaintained deprecation banner

Any run-phase reference page that describes the `cao_rest` or `houmao_server_rest` backends SHALL open the relevant section with a prominent, bold-prefixed deprecation banner identifying the content as unmaintained and possibly incorrect.

At minimum, `docs/reference/realm_controller.md` SHALL include such a banner immediately before the descriptive content for `cao_rest` and immediately before the descriptive content for `houmao_server_rest`. The same banner SHALL appear on `docs/reference/codex-cao-approval-prompt-troubleshooting.md` after it is moved out of the retired agents subtree.

The banner SHALL state, at a minimum:

- that the backend remains in the codebase as a legacy escape hatch,
- that the documentation is no longer actively maintained,
- that the content below may be incorrect or stale,
- and that readers should prefer the current maintained backends (for example `local_interactive`) for new work.

The banner SHALL appear before any descriptive prose, option tables, or workflow diagrams for the deprecated backend. Inline mentions of `cao_rest` or `houmao_server_rest` in lists or tables (for example a backend enumeration) do not by themselves require the banner — only dedicated sections that describe how to use, configure, or troubleshoot the backend trigger the banner requirement.

#### Scenario: Reader opens the realm_controller reference page and reaches the cao_rest section

- **WHEN** a reader scrolls to the `cao_rest` section of `docs/reference/realm_controller.md`
- **THEN** a bold-prefixed deprecation banner appears before any descriptive prose
- **AND THEN** the banner states the backend is unmaintained and the content may be incorrect

#### Scenario: Reader opens the realm_controller reference page and reaches the houmao_server_rest section

- **WHEN** a reader scrolls to the `houmao_server_rest` section of `docs/reference/realm_controller.md`
- **THEN** a bold-prefixed deprecation banner appears before any descriptive prose
- **AND THEN** the banner states the backend is unmaintained and the content may be incorrect

#### Scenario: Reader opens the moved codex CAO approval troubleshooting page

- **WHEN** a reader opens `docs/reference/codex-cao-approval-prompt-troubleshooting.md`
- **THEN** a bold-prefixed deprecation banner appears at the top of the page
- **AND THEN** the banner states the content is retained only as historical troubleshooting for the deprecated `cao_rest` backend and may be incorrect

### Requirement: Run-phase reference explains provider-native relaunch continuation
The run-phase reference SHALL document provider-native chat continuation during tmux-backed relaunch.

The session-lifecycle reference SHALL explain that relaunch reuses the managed session home and tmux window `0`, while the optional relaunch chat-session selector controls whether the provider starts fresh or resumes provider-native history.

The backend reference SHALL include provider-native startup mappings for every maintained local-interactive and native headless relaunch path. For Kimi 2.1.1 and later, it SHALL show `--auto` combined with `--continue` or `--session <session_id>` for unattended TUI relaunch, preserve `--model <alias>`, and explain that the native `SYSTEM.md` contract is validated before respawn.

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
- **THEN** it documents the `>=2.1.1` resume, auto-mode, model, update-suppression, and native prompt constraints
- **AND THEN** it states that role and policy chat bootstraps are absent

#### Scenario: Reader sees Kimi-specific relaunch and prompt constraints
- **WHEN** a reader opens the Kimi Code local-interactive backend reference
- **THEN** it documents native resume arguments, native auto mode, model selection, managed update suppression, and pre-start `SYSTEM.md` validation
- **AND THEN** it documents no post-readiness policy or role bootstrap command

### Requirement: Run-phase reference documents Kimi unattended TUI startup and relaunch
The run-phase backend and lifecycle references SHALL document that maintained Kimi Code 2.1.1-or-later local-interactive sessions can run with `operator_prompt_mode = unattended` while remaining visible TUI sessions.

The reference SHALL explain that unattended Kimi TUI startup uses native `--auto` after native managed-home role-prompt projection and that maintained Kimi 2.1.1-or-later behavior accepts this flag with `--continue` and `--session <session_id>`. It SHALL state that Houmao sends neither an auto-mode chat command nor a role-bootstrap chat turn.

The reference SHALL distinguish Kimi `as_is` TUI launch from unattended TUI launch, identify 2.1.1 as the minimum maintained version, state that Kimi releases before it are unsupported, and state that support has no upper version limit.

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
- **THEN** the documentation describes the Kimi `>=2.1.1` native `SYSTEM.md` integration from current baseline source evidence
- **AND THEN** it presents no below-floor compatibility path

### Requirement: Run-phase reference excludes Gemini
Maintained backend, launch-plan, manifest, lifecycle, role-injection, gateway, and realm-controller documentation SHALL not describe Gemini runtime behavior.

#### Scenario: Runtime reference lists backends
- **WHEN** a reader inspects current run-phase backend and schema guidance
- **THEN** `gemini_cli` and `gemini_headless` are absent from supported values and examples
