## ADDED Requirements

### Requirement: Managed Kimi role prompts use native SYSTEM.md projection
For maintained Kimi Code >=2.1.1, Houmao SHALL project the complete effective launch prompt into `<KIMI_CODE_HOME>/SYSTEM.md` before provider start, preserving built-in instructions with leading `${base_prompt}`. Native projection SHALL validate placeholders and prompt precedence, enforce the v2 engine, remove stale managed files for empty prompts, and record typed provenance.

#### Scenario: Non-empty Kimi role prompt is native before startup
- **WHEN** Houmao builds and launches a Kimi 2.1.1-or-later brain whose effective launch prompt is non-empty
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

#### Scenario: Bare-dollar prompt text remains literal
- **WHEN** effective Houmao prompt text contains bare dollar signs or other text outside Kimi's `${identifier}` placeholder grammar
- **THEN** projection preserves those bytes unchanged
- **AND THEN** every token inside that grammar is rejected even if the baseline Kimi release does not recognize its name, because Kimi provides no escape syntax

#### Scenario: Brain manifest records native prompt provenance
- **WHEN** brain construction projects a managed Kimi native role prompt
- **THEN** the brain manifest records the native injection method, managed relative path, effective-prompt digest, projected-file digest, and required Kimi engine
- **AND THEN** provenance introduces no secret content beyond the effective prompt already owned by the managed brain

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
**Reason**: Maintained providers must use a deterministic native pre-turn system-prompt surface; Kimi 2.1.1 and later provide one.

**Migration**: Rebuild Kimi brains with Kimi Code 2.1.1 or later so Houmao writes the role prompt to `<KIMI_CODE_HOME>/SYSTEM.md`.

### Requirement: Runtime supports auto-skill system-prompt role injection
**Reason**: Skill activation did not prove that the role prompt was applied before substantive work and is no longer part of the maintained launch contract.

**Migration**: Use the native system-prompt injection selected by the qualified provider launch strategy.
