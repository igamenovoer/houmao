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

The run-phase reference SHALL include a page documenting role injection: how `plan_role_injection()` produces a `RoleInjectionPlan` with backend-specific strategies. The reference SHALL explain the rationale for per-backend differences.

The `RoleInjectionMethod` enumeration in the docs SHALL use the literal values from the code type: `native_developer_instructions`, `native_append_system_prompt`, `bootstrap_message`, and `cao_profile`. The docs SHALL NOT use the stale name `profile_based`.

The per-backend strategy table and Mermaid diagram SHALL use `cao_profile` for the `cao_rest` and `houmao_server_rest` backends.

#### Scenario: Reader understands why role injection differs by backend

- **WHEN** a reader opens the role-injection page
- **THEN** they find a table or list mapping each backend to its injection method with a rationale for the difference

#### Scenario: Reader sees correct RoleInjectionMethod values

- **WHEN** a reader checks the `RoleInjectionMethod` enumeration in the role injection reference
- **THEN** the listed values are `native_developer_instructions`, `native_append_system_prompt`, `bootstrap_message`, and `cao_profile`
- **AND THEN** the name `profile_based` does not appear anywhere on the page

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

The backend reference SHALL include the provider-native startup mapping for Claude Code, Codex, Kimi Code, and Gemini CLI for local interactive relaunch paths and for each provider's maintained native headless relaunch path.

The backend reference SHALL document that Kimi Code TUI resumed startup cannot combine `--continue` or `--session <session_id>` with `--yolo`, `--auto`, or `--plan`, and that `--model <alias>` remains valid with resumed startup.

The backend or launch reference SHALL document that managed `--skills-dir` projection remains Kimi headless prompt-mode behavior and is not claimed for Kimi TUI launch.

The backend or launch reference SHALL document that managed Kimi TUI launches suppress the interactive update preflight by setting `KIMI_CODE_NO_AUTO_UPDATE=1`.

Run-phase reference pages SHALL present Kimi Code before Gemini in neutral provider lists while preserving backend-specific accuracy. Run-phase diagrams or compact examples that list only three providers SHALL include Claude, Codex, and Kimi.

Run-phase references that explain Kimi role injection SHALL warn that Kimi Code 0.11.0 does not expose a native system-prompt flag. The warning SHALL state that Kimi role delivery can rely on bootstrap or managed auto-skill workflows, and that Kimi users may need to invoke `houmao-auto-system-prompt` manually before substantive chat begins when automatic skill startup has not confirmed the prompt.

The launch-profile guide or linked run-phase documentation SHALL explain that launch-profile relaunch chat-session policy applies only to later relaunch of instances created from that profile and does not resume provider history on first launch.

#### Scenario: Reader understands TUI relaunch continuation
- **WHEN** a reader opens the run-phase session lifecycle or backend reference
- **THEN** the documentation explains that TUI relaunch continuation is implemented by provider-native startup args before the TUI is respawned
- **AND THEN** it distinguishes that behavior from sending `/resume` or another prompt after startup

#### Scenario: Reader understands launch-profile relaunch policy scope
- **WHEN** a reader opens launch-profile or run-phase documentation for relaunch chat-session policy
- **THEN** the documentation states that the policy applies to relaunch of future instances created from the profile
- **AND THEN** it states that first launch remains normal fresh provider startup

#### Scenario: Reader sees provider mapping table
- **WHEN** a reader needs to verify provider behavior for relaunch continuation
- **THEN** the backend reference includes the Claude Code, Codex, Kimi Code, and Gemini CLI native command forms for maintained TUI and headless latest/exact continuation paths

#### Scenario: Reader sees Kimi-specific launch constraints
- **WHEN** a reader opens the Kimi Code local interactive backend reference
- **THEN** the documentation describes Kimi resume conflicts with `--yolo`, `--auto`, and `--plan`
- **AND THEN** it explains that `--model <alias>` is still allowed and that managed update preflight suppression uses `KIMI_CODE_NO_AUTO_UPDATE=1`

### Requirement: Run-phase reference documents Kimi unattended TUI startup and relaunch
The run-phase backend and lifecycle references SHALL document that Kimi Code local-interactive sessions can run with `operator_prompt_mode = unattended` while remaining visible TUI sessions.

The reference SHALL explain that unattended Kimi TUI startup enters Kimi auto permission mode before managed prompts are submitted.

The reference SHALL explain that resumed Kimi TUI startup cannot combine Kimi native resume selectors with `--auto`, so Houmao preserves Kimi resume arguments and refreshes auto mode after TUI readiness.

The reference SHALL distinguish Kimi `as_is` TUI launch from unattended TUI launch.

#### Scenario: Reader sees Kimi TUI unattended behavior
- **WHEN** a reader opens the run-phase backend reference for Kimi Code local-interactive launch
- **THEN** it states that unattended Kimi TUI launch runs in Kimi auto permission mode
- **AND THEN** it states that Houmao applies that mode before role bootstrap or workload prompts

#### Scenario: Reader sees Kimi resumed startup constraint
- **WHEN** a reader opens the run-phase relaunch reference for Kimi Code local-interactive launch
- **THEN** it explains that `--continue` and `--session <session_id>` cannot be combined with `--auto`
- **AND THEN** it explains that Houmao refreshes auto mode after TUI readiness for unattended resumed sessions

#### Scenario: Reader can distinguish as-is from unattended
- **WHEN** a reader compares Kimi launch prompt modes in run-phase documentation
- **THEN** `as_is` is described as preserving provider approval behavior
- **AND THEN** `unattended` is described as the maintained no-question mode

#### Scenario: Reader sees Kimi native system-prompt gap

- **WHEN** a reader opens the Kimi role-injection or backend reference
- **THEN** the docs state that Kimi Code 0.11.0 lacks a native system-prompt flag
- **AND THEN** the docs state that `houmao-auto-system-prompt` may require manual invocation before substantive Kimi chat begins when automatic loading has not happened
