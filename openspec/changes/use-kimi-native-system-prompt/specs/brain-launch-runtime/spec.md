## ADDED Requirements

### Requirement: Managed Kimi role prompts use native SYSTEM.md projection
For a maintained Kimi Code launch at version 0.34.0 or later, Houmao SHALL project the complete effective launch prompt into `<KIMI_CODE_HOME>/SYSTEM.md` before the provider starts. The managed file SHALL preserve Kimi's built-in default instructions through a leading `${base_prompt}` reference.

Before projection, Houmao SHALL reject an effective prompt containing any `${identifier}` token that matches Kimi's template-placeholder grammar because Kimi provides no escape syntax and later versions may assign meaning to names that 0.34 does not recognize. Bare dollar signs and text outside that grammar MAY remain unchanged.

Houmao SHALL force the Kimi v2 engine for managed launches that rely on this file. If the effective launch prompt is empty, brain construction SHALL remove a stale Houmao-managed `SYSTEM.md` rather than retain instructions from an earlier build.

Launch planning SHALL reject explicit agent selectors, explicit agent files, or discovered default-agent overrides that take precedence over `SYSTEM.md`. The diagnostic SHALL identify the conflicting surface before the provider process starts.

The brain manifest SHALL record the native injection method, managed relative path, effective-prompt digest, projected-file digest, and Kimi engine requirement without storing secrets beyond the prompt content already owned by the managed brain.

#### Scenario: Non-empty Kimi role prompt is native before startup
- **WHEN** Houmao builds and launches a Kimi 0.34.0-or-later brain whose effective launch prompt is non-empty
- **THEN** `<KIMI_CODE_HOME>/SYSTEM.md` contains the built-in prompt reference followed by the complete effective Houmao prompt
- **AND THEN** the Kimi process uses the v2 engine and starts only after projection succeeds

#### Scenario: Kimi template placeholder in a role is rejected
- **WHEN** the effective Houmao prompt contains a token such as `${cwd}`, `${base_prompt}`, or `${future_name}`
- **THEN** projection fails with a diagnostic that identifies the placeholder token
- **AND THEN** Houmao does not start Kimi with silently substituted role text

#### Scenario: Empty effective prompt removes stale managed state
- **WHEN** a Kimi brain is rebuilt with no effective launch prompt after an earlier build projected `SYSTEM.md`
- **THEN** the stale Houmao-managed `SYSTEM.md` is absent before provider start
- **AND THEN** the manifest records that no native role prompt was projected

#### Scenario: Higher-priority Kimi agent override is rejected
- **WHEN** a managed Kimi launch would select an explicit or discovered main-agent definition that takes precedence over `SYSTEM.md`
- **THEN** launch fails with a diagnostic naming the conflicting agent-selection surface
- **AND THEN** no Kimi process starts with an unverified role prompt

## MODIFIED Requirements

### Requirement: Runtime rejects unsupported system-prompt fallback cases
When a managed agent requires an effective role or system prompt, runtime planning SHALL fail clearly if the selected tool, backend, and qualified version do not declare a native system-prompt mechanism that applies before the first user turn.

The runtime SHALL NOT fall back to managed auto skills, memo-only injection, or ordinary chat bootstrap to compensate for a missing native system-prompt mechanism.

#### Scenario: Tool without native prompt support fails
- **WHEN** a managed launch requires a role or system prompt
- **AND WHEN** the selected tool capability metadata declares no applicable native system-prompt mechanism
- **THEN** launch planning fails with a diagnostic that names the unsupported system-prompt injection path
- **AND THEN** no provider process is started with a skill, memo, or chat-only fallback

#### Scenario: Tool without native prompt or startup-visible skills fails
- **WHEN** a managed launch requires a role or system prompt and the selected tool has no native prompt surface
- **THEN** launch planning fails even if the tool supports startup-visible skills
- **AND THEN** no provider process is started through the retired skill fallback

## REMOVED Requirements

### Requirement: Brain construction projects required managed auto skills
**Reason**: Maintained providers must use a deterministic native pre-turn system-prompt surface; Kimi 0.34.0 and later provide one.

**Migration**: Rebuild Kimi brains with Kimi Code 0.34.0 or later so Houmao writes the role prompt to `<KIMI_CODE_HOME>/SYSTEM.md`.

### Requirement: Runtime supports auto-skill system-prompt role injection
**Reason**: Skill activation did not prove that the role prompt was applied before substantive work and is no longer part of the maintained launch contract.

**Migration**: Use the native system-prompt injection selected by the qualified provider launch strategy.
