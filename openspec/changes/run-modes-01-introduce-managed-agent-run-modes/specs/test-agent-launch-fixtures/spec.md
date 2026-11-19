# Spec Delta

## ADDED Requirements

### Requirement: Fixture qualification records build and evidence for each native run mode

Qualification SHALL record build, model, protocol, case, run mode, backend, native surface, and outcome without credentials. Exercise every qualified client/mode pair with DeepSeek and its supported surfaces. Self-hosted runs SHALL use an explicitly configured model other than Qwen3.8 when available and record missing prerequisites.

#### Scenario: Self-hosted endpoint is not configured
- **WHEN** live qualification has no configured compatible self-hosted endpoint/model
- **THEN** its report marks those live lanes as not run with the missing prerequisite
- **AND THEN** passing hermetic tests do not become a live qualification claim

#### Scenario: Historical capture records Qwen usage
- **WHEN** an existing sanitized accounting fixture records an earlier Qwen capture
- **THEN** it retains its factual model/version metadata
- **AND THEN** maintained launch helpers do not depend on the historical change-local wrapper

#### Scenario: DSH Service Evidence Identifies Its Mode
- **WHEN** a DSH ACP cloud smoke passes
- **THEN** its report records service with the qualified ACP backend
- **AND THEN** Claude, Codex, and Kimi retain their required headless and unattended TUI lanes

#### Scenario: DSH Web Qualification Uses the Native Browser Surface
- **WHEN** a DSH fixture selects `mode=web`
- **THEN** qualification launches its Web Host and records Web API and browser evidence
- **AND THEN** a tmux log capture or passing ACP run does not qualify the interactive lane

## MODIFIED Requirements

### Requirement: Automated test launches default to unattended posture

Every supported fixture run mode SHALL request unattended posture by default. Client-specific invocation SHALL use qualified flags and bootstrap configuration for the installed version. The helper SHALL preserve the distinction between the chosen entrypoint, its supported native controls, and the independent operator prompt policy.

#### Scenario: Kimi prompt mode is selected
- **WHEN** a Kimi headless launch uses its noninteractive prompt mode
- **THEN** the command does not add a TUI-only unattended flag that conflicts with that mode

#### Scenario: TUI preparation encounters an unsupported startup prompt
- **WHEN** the installed client cannot satisfy the selected unattended launch contract
- **THEN** qualification reports that limitation rather than recording an interactive stall as a passing run

### Requirement: DSH Web Fixtures Share the Existing Generic Endpoint Cases

DSH `web` fixture preparation SHALL reuse the `self-hosted` and `cloud-api` cases, `DshToolParams` compatibility and reasoning inputs, and private credential/run roots established for headless DSH. Raw and managed preparation SHALL expose the same native Web behavior. Browser startup and connection credentials SHALL remain controlled locally without entering tracked reports.

#### Scenario: A Fresh Host Uses Cloud DSH Interactively
- **WHEN** a developer configures only the selected DeepSeek key, endpoint, and model
- **THEN** a DSH Web test agent can be prepared without a self-hosted model, auth JSON, or desktop display

#### Scenario: A Browser Connects to the Managed Fixture
- **WHEN** a qualification browser signs in through the fixture's private local connection mechanism
- **THEN** it opens the same native session targeted by the programmatic adapter
- **AND THEN** public fixture summaries contain only non-secret location and identity metadata

#### Scenario: Self-Hosted Web Fixture Shares Tool-Params Compatibility Inputs
- **WHEN** a developer prepares a `mode=web` self-hosted `pi-ai/openai-completions` DSH fixture with explicit `compat` and `reasoning_efforts` settings
- **THEN** raw and managed Web preparations emit the same DSH `tool_params` compatibility, reasoning, and endpoint-only contract as headless DSH

### Requirement: Automated fixture tests use synthetic credentials

Unit and integration coverage SHALL exercise both cases, the qualified tool/mode matrix, credential discovery/import, and mode-specific preparation with synthetic credentials and controlled endpoints/processes. Default automated tests SHALL NOT require the developer's env file, saved vendor login, or cloud access.

#### Scenario: CI runs without local accounts
- **WHEN** automated fixture tests execute on a machine without live credentials
- **THEN** the hermetic suite validates resolution and lifecycle wiring without reading personal auth state or issuing paid requests

## REMOVED Requirements

### Requirement: Fixture qualification records actual evidence and limitations

**Reason**: Old scenario identities assigned DSH ACP to headless and its browser to TUI.

**Migration**: Label native one-shot, service, TUI, and Web evidence with the selected mode, backend, and actual surface.
