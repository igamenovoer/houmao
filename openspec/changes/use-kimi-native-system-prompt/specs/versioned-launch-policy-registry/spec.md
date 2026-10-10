## MODIFIED Requirements

### Requirement: Registry declares maintained Kimi unattended strategy coverage
The launch-policy registry SHALL include maintained Kimi Code unattended strategy coverage for the `kimi_headless` backend and for the `raw_launch` backend used by Kimi Code local-interactive TUI launch. The compatible version expression SHALL be `>=0.34.0` with no upper version limit; no strategy SHALL match an earlier Kimi version.

That Kimi strategy coverage SHALL declare the minimal provider-ready inputs, current source and live-probe evidence, runtime-owned startup surfaces, v2-engine requirement, native `SYSTEM.md` system-prompt surface, ordered pre-launch actions, and validation required before Kimi starts.

For `kimi_headless`, maintained coverage SHALL avoid prompt-mode-incompatible startup flags such as `--auto`, `--yolo`, and `--plan`. For `raw_launch`, maintained unattended coverage SHALL add native `--auto` to fresh and resumed TUI startup commands and SHALL NOT submit a conversational command to establish launch policy. Credential readiness SHALL remain separate from unattended and system-prompt compatibility.

#### Scenario: Maintainer inspects Kimi 0.34 strategy metadata
- **WHEN** a maintainer inspects the maintained Kimi headless and local-interactive strategies
- **THEN** both declare the minimum-only `>=0.34.0` range and current baseline evidence
- **AND THEN** both declare v2-engine and native `SYSTEM.md` ownership separately from credential readiness

#### Scenario: Pre-0.34 Kimi launch is rejected
- **WHEN** a managed Kimi launch detects a version earlier than 0.34.0
- **THEN** the registry reports that no compatible strategy exists
- **AND THEN** launch fails without selecting a legacy or best-effort path

#### Scenario: Newer Kimi launch uses the minimum-version strategy
- **WHEN** a managed Kimi launch detects Kimi 0.35.0 or any later parseable version
- **THEN** the registry selects the maintained `>=0.34.0` strategy
- **AND THEN** it does not impose an upper-version compatibility failure

#### Scenario: Headless and resumed TUI commands remain valid
- **WHEN** a compatible Kimi 0.34.0-or-later strategy resolves an unattended launch
- **THEN** headless mode excludes prompt-mode-incompatible permission flags
- **AND THEN** fresh or resumed TUI mode includes native `--auto` without a policy-changing chat command

#### Scenario: Maintainer inspects Kimi headless unattended strategy metadata
- **WHEN** a maintainer inspects the maintained Kimi headless strategy
- **THEN** the entry declares `kimi_headless`, the minimum-only `>=0.34.0` range, evidence, owned startup surfaces, and validation
- **AND THEN** credential readiness remains distinct from unattended startup and native role-prompt ownership

#### Scenario: Maintainer inspects Kimi TUI unattended strategy metadata
- **WHEN** a maintainer inspects the maintained Kimi local-interactive unattended strategy
- **THEN** the entry declares `raw_launch`, native `--auto`, native `SYSTEM.md`, and v2-engine ownership
- **AND THEN** it declares no runtime policy or role chat bootstrap action

#### Scenario: Kimi headless strategy rejects prompt-mode-incompatible launch args
- **WHEN** a compatible Kimi headless unattended strategy receives `--auto`, `--yolo`, or `--plan`
- **THEN** the strategy rejects or removes those arguments before provider start
- **AND THEN** the final prompt-mode command remains valid and unattended

#### Scenario: Kimi resumed TUI keeps native auto mode
- **WHEN** a compatible unattended Kimi TUI launch resumes through `--continue` or `--session <session_id>`
- **THEN** the final provider command also contains `--auto`
- **AND THEN** Houmao sends no policy-changing chat command after readiness

#### Scenario: Unknown Kimi version does not silently use maintained strategy
- **WHEN** a Kimi unattended launch reports an unparseable version or a version below 0.34.0
- **THEN** the registry reports that no compatible strategy exists
- **AND THEN** launch fails explicitly

#### Scenario: Kimi TUI strategy owns automatic permission config
- **WHEN** the runtime resolves a compatible Kimi TUI unattended strategy
- **THEN** strategy-owned permission inputs resolve to auto mode before provider start
- **AND THEN** unrelated Kimi provider, model, OAuth, skill, and telemetry config remains intact

## ADDED Requirements

### Requirement: Launch policy declares native system-prompt capabilities
The launch-policy registry SHALL model native provider system-prompt capability separately from unattended startup capability and provider skill support.

For each supported tool, backend, and version strategy that participates in managed role injection, resolved metadata SHALL identify the native injection method, owned provider-home path or launch surface, precedence conflicts that can bypass it, required engine mode, and evidence for application before the first user turn.

Provider skill installation or startup-visible skill metadata SHALL NOT qualify as a system-prompt fallback.

#### Scenario: Kimi strategy declares native home prompt evidence
- **WHEN** a maintainer inspects a maintained Kimi 0.34.0-or-later strategy
- **THEN** the metadata identifies `<KIMI_CODE_HOME>/SYSTEM.md` as the native system-prompt surface
- **AND THEN** it identifies Kimi agent-selection precedence and v2-engine constraints that launch validation must enforce

#### Scenario: Skill support is not prompt support
- **WHEN** a provider strategy declares that skill files can be installed or are visible at startup
- **AND WHEN** it declares no native system-prompt surface
- **THEN** launch policy does not treat the skill capability as supported role injection

### Requirement: Launch policy requires native system-prompt injection
When a managed launch requires a role or system prompt, launch policy SHALL select the qualified provider strategy's native system-prompt method. It SHALL produce an explicit incompatibility result if the strategy has no applicable native method or if a higher-precedence provider input would bypass that method.

#### Scenario: Kimi selects native home system prompt
- **WHEN** a maintained Kimi 0.34.0-or-later launch requires a Houmao role or system prompt
- **THEN** launch policy selects the native managed-home `SYSTEM.md` method
- **AND THEN** it selects neither managed auto-skill injection nor ordinary chat bootstrap

#### Scenario: Unsupported provider reports incompatibility
- **WHEN** a managed launch requires a role or system prompt
- **AND WHEN** the qualified strategy has no applicable native system-prompt method
- **THEN** strategy resolution reports that no supported injection method exists for that tool, backend, and version

## REMOVED Requirements

### Requirement: Launch policy selects auto-skill system-prompt injection for eligible non-native tools
**Reason**: Startup-visible skill metadata cannot guarantee that the effective role prompt is applied before the first substantive turn.

**Migration**: Declare and use a qualified native system-prompt method or reject the managed launch.

### Requirement: Launch policy declares system-prompt bootstrap capabilities
**Reason**: The old capability model encoded startup-visible skills as a maintained prompt fallback.

**Migration**: Declare a qualified native provider system-prompt method with owned surfaces, precedence constraints, and evidence.
