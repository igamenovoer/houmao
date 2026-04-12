## ADDED Requirements

### Requirement: `houmao-agent-instance` launch guidance preserves foreground-first gateway posture
The packaged `houmao-agent-instance` launch action guidance SHALL preserve foreground-first gateway posture whenever it teaches a launch lane that may start or inherit gateway attachment.

For specialist-backed launch through `project easy instance launch`, the guidance SHALL defer detailed launch-time gateway behavior to `houmao-specialist-mgr` while still stating that agents MUST NOT add background gateway flags unless the user explicitly requests detached background gateway execution.

For explicit launch-profile-backed managed launch, the guidance SHALL state that stored launch-profile gateway posture may already control gateway auto-attach, and agents SHALL NOT add one-shot background gateway overrides unless the user explicitly requests background gateway execution.

For direct role or preset launch through `agents launch`, the guidance SHALL avoid treating gateway attach as part of launch completion, while preserving the rule that any later gateway attach should go through `houmao-agent-gateway` foreground-first lifecycle guidance.

#### Scenario: Specialist-backed instance launch does not add background gateway flags
- **WHEN** an agent follows `houmao-agent-instance` launch guidance for the specialist-backed lane
- **AND WHEN** the user has not explicitly requested background gateway execution
- **THEN** the guidance does not add `--gateway-background` or another detached gateway override
- **AND THEN** it points detailed specialist-backed launch semantics to `houmao-specialist-mgr`

#### Scenario: Launch-profile lane does not override stored gateway posture silently
- **WHEN** an agent follows `houmao-agent-instance` guidance for `agents launch --launch-profile <profile>`
- **AND WHEN** the user has not explicitly requested a background gateway override
- **THEN** the guidance does not add a one-shot background gateway override
- **AND THEN** it treats the stored profile gateway posture as the source of launch-time gateway defaults

#### Scenario: Later gateway attach routes through foreground-first gateway guidance
- **WHEN** an agent completes a managed-agent launch where gateway attach is not part of launch completion
- **AND WHEN** the user then asks to attach or operate the live gateway
- **THEN** the guidance routes that follow-up through `houmao-agent-gateway`
- **AND THEN** the follow-up attach inherits the foreground-first and explicit-background rule from the gateway lifecycle guidance
