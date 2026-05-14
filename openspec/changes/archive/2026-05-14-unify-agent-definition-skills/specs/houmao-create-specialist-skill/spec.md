## ADDED Requirements

### Requirement: `houmao-specialist-mgr` is no longer the canonical specialist-management skill
The system SHALL treat `houmao-agent-definition` as the canonical packaged skill for specialist and easy-profile authoring.

If `houmao-specialist-mgr` remains packaged, it SHALL act as a compatibility wrapper that routes users to the corresponding `houmao-agent-definition` easy subskill and states that `houmao-agent-definition` is the canonical current skill.

#### Scenario: Old specialist skill invocation redirects to unified skill
- **WHEN** a user or installed agent invokes `houmao-specialist-mgr` for specialist or easy-profile authoring
- **THEN** the skill tells the agent to use the corresponding `houmao-agent-definition` easy subskill
- **AND THEN** it does not present itself as the independent canonical owner of specialist and easy-profile workflows

### Requirement: Existing specialist behavior is preserved inside unified easy subskills
The unified `houmao-agent-definition` easy subskills SHALL preserve the supported specialist and easy-profile authoring behavior previously documented by `houmao-specialist-mgr`, including create, set, list, get, remove, profile create, profile set, easy launch, and easy stop routing.

The unified guidance SHALL still tell users that broad follow-up live-agent lifecycle management belongs to `houmao-agent-instance` after easy launch or stop.

#### Scenario: Specialist update still uses project easy specialist set
- **WHEN** a user asks to patch an existing specialist through the unified skill
- **THEN** the unified easy specialist subskill routes the request through `houmao-mgr project easy specialist set`
- **AND THEN** it does not remove and recreate the specialist for ordinary prompt, skill, setup, credential, prompt-mode, model, reasoning-level, or env edits
