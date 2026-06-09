## ADDED Requirements

### Requirement: Launch policy declares system-prompt bootstrap capabilities
The launch-policy registry SHALL model provider system-prompt bootstrap capability separately from unattended startup capability.

For each supported tool/backend/version strategy that participates in managed role injection, the registry or resolved strategy metadata SHALL declare whether the provider supports native system-prompt injection, whether it supports provider skills, and whether skill metadata is visible in the provider's native startup or post-compaction context.

Skill-based system-prompt fallback SHALL require startup-visible skill metadata, not merely the ability to install skill files.

#### Scenario: Kimi strategy declares startup-visible skill bootstrap evidence
- **WHEN** a maintainer inspects a maintained Kimi launch-policy strategy that lacks native system-prompt support
- **THEN** the strategy metadata declares that Kimi has provider skills and startup-visible skill metadata for the supported version range
- **AND THEN** the evidence identifies the source or probe basis for that startup-visible skill assumption

#### Scenario: Generic skill installation is insufficient for fallback
- **WHEN** a future provider strategy declares that skill files can be installed
- **AND WHEN** it does not declare that skill metadata is visible in native startup or post-compaction context
- **THEN** launch policy does not select auto-skill system-prompt injection for that strategy

### Requirement: Launch policy selects auto-skill system-prompt injection for eligible non-native tools
When a managed launch requires a role/system prompt and the selected provider strategy lacks native system-prompt injection but declares startup-visible skill metadata support, launch policy SHALL select the auto-skill system-prompt role injection method.

When the selected provider strategy declares native system-prompt injection, launch policy SHALL prefer native injection over auto-skill fallback.

When the selected provider strategy declares neither native system-prompt injection nor startup-visible skill metadata support, launch policy SHALL produce an explicit incompatibility result.

#### Scenario: Kimi uses auto-skill injection instead of bootstrap chat
- **WHEN** a maintained Kimi strategy for a supported version lacks CLI-native system-prompt injection
- **AND WHEN** the strategy declares startup-visible skill metadata support
- **AND WHEN** managed launch requires a Houmao role/system prompt
- **THEN** launch policy selects auto-skill system-prompt injection
- **AND THEN** it does not select ordinary chat bootstrap as the maintained method

#### Scenario: Native prompt provider keeps native injection
- **WHEN** a maintained provider strategy declares native system-prompt injection support
- **AND WHEN** managed launch requires a Houmao role/system prompt
- **THEN** launch policy selects the native role injection method for that provider
- **AND THEN** it does not inject `houmao-auto-system-prompt` only to replace a native provider instruction surface

#### Scenario: Unsupported provider reports incompatibility
- **WHEN** a maintained provider strategy declares no native system-prompt support and no startup-visible skill metadata support
- **AND WHEN** managed launch requires a Houmao role/system prompt
- **THEN** strategy resolution reports that no supported system-prompt injection method exists for that provider/backend/version
