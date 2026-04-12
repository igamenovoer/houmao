## ADDED Requirements

### Requirement: `houmao-adv-usage-pattern` gateway-attach references defer to foreground-first lifecycle guidance
When a packaged `houmao-adv-usage-pattern` page mentions gateway attach or gateway discovery as part of a composed workflow, that page SHALL route attach posture decisions to `houmao-agent-gateway`.

Composition guidance SHALL NOT present background gateway execution as implicit setup for advanced usage patterns.

If an advanced usage pattern requires or recommends that a live gateway already be attached, the pattern guidance SHALL treat foreground same-session auxiliary-window attach as the default for tmux-backed managed sessions and detached background gateway execution as explicit user intent governed by `houmao-agent-gateway`.

#### Scenario: Self-wakeup pattern delegates gateway attach posture
- **WHEN** the self-wakeup via self-mail pattern tells the agent to use `houmao-agent-gateway` for gateway attach or discovery
- **THEN** the pattern guidance defers attach posture selection to `houmao-agent-gateway`
- **AND THEN** it does not imply that background gateway execution is the default setup for the pattern

#### Scenario: Advanced pattern background gateway execution remains explicit
- **WHEN** an advanced usage pattern needs a live gateway and the user has not explicitly requested background gateway execution
- **THEN** the pattern guidance does not tell the agent to choose a background gateway launch or attach path
- **AND THEN** it preserves the foreground-first gateway lifecycle rule from the owning gateway skill
