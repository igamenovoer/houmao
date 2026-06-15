## ADDED Requirements

### Requirement: Brain construction projects required managed auto skills
When a launch plan selects an auto-skill based role injection method, brain construction SHALL project the required packaged auto skills into the managed home before provider start.

Auto-skill projection SHALL use the same provider-visible skill destination root as ordinary managed skill projection for that tool, such as `skills/` for Kimi and `.gemini/skills/` for Gemini.

Auto-skill projection SHALL be independent from project skill selection, profile-private skill projection, and managed system-skill selection.

Auto-skill projection SHALL be counted as projected skill content for provider setup that needs a skill root registration, including Kimi `extra_skill_dirs`.

Brain construction SHALL record auto-skill provenance including selected auto-skill names, the selection reason, projected relative directories, and the destination root.

#### Scenario: Kimi home registers skill root when only auto skill is projected
- **WHEN** brain construction builds a Kimi managed home whose only projected skill is `houmao-auto-system-prompt`
- **THEN** the managed home contains the projected skill under the Kimi-visible skill root
- **AND THEN** Kimi configuration registers that projected skill root for discovery
- **AND THEN** construction provenance records the auto-skill selection and projected relative directory

#### Scenario: Disabled system-skill policy does not suppress required auto skill
- **WHEN** managed launch resolves a system-skill policy that installs no system skills
- **AND WHEN** the role injection method requires `houmao-auto-system-prompt`
- **THEN** brain construction still projects `houmao-auto-system-prompt`
- **AND THEN** construction provenance distinguishes the auto-skill projection from the empty system-skill selection

### Requirement: Runtime supports auto-skill system-prompt role injection
The runtime SHALL support a role injection method that stores the effective Houmao system prompt for self-service retrieval and uses `houmao-auto-system-prompt` as the provider bootstrap path.

For this method, runtime startup SHALL NOT send the effective Houmao system prompt as an ordinary chat bootstrap message.

Runtime manifests SHALL describe the method as auto-skill based and SHALL record the prompt reference or hash needed for diagnostics without claiming the provider has applied the prompt solely because the skill was projected.

#### Scenario: Auto-skill role injection does not send chat bootstrap
- **WHEN** a Kimi managed launch resolves auto-skill system-prompt injection
- **THEN** the launch plan does not include a chat bootstrap message containing the effective Houmao system prompt
- **AND THEN** the managed home includes `houmao-auto-system-prompt`
- **AND THEN** the effective prompt remains available to `houmao-mgr agents self system-prompt show --format text`

#### Scenario: Manifest records projected but not applied
- **WHEN** a managed launch projects `houmao-auto-system-prompt`
- **THEN** the runtime or construction manifest records that the auto skill was projected
- **AND THEN** the manifest does not report the system prompt as applied unless a supported observable signal proves the provider loaded it

### Requirement: Runtime rejects unsupported system-prompt fallback cases
When a managed agent requires an effective role or system prompt, runtime planning SHALL fail clearly if the selected tool has neither native system-prompt support nor startup-visible skill metadata support.

The runtime SHALL NOT silently fall back to memo-only injection or ordinary chat bootstrap for such tools.

#### Scenario: Tool without native prompt or startup-visible skills fails
- **WHEN** a managed launch requires a role/system prompt
- **AND WHEN** the selected tool capability metadata declares no native system-prompt support and no startup-visible skill metadata support
- **THEN** launch planning fails with a diagnostic that names the unsupported system-prompt injection path
- **AND THEN** no provider process is started with a best-effort memo or chat-only fallback
