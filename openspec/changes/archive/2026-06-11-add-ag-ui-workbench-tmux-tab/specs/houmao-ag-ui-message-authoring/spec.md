## ADDED Requirements

### Requirement: Houmao gateway publish helper can omit explicit routing
The Houmao AG-UI publish helper SHALL allow callers to omit explicit AG-UI routing when targeting a Houmao gateway.

When explicit routing is omitted, the publish helper SHALL submit the validated AG-UI event batch to the Houmao gateway in a form that allows gateway destination fallback.

Explicit `connectionId`, `threadId`, or `runId` options SHALL remain available and SHALL take priority over last-sent-thread, last-bound-thread, and default sink fallback.

When the gateway routes through last-sent-thread or last-bound-thread, the publish helper SHALL report the gateway publish result, including accepted and delivered counts.

When the gateway reports that it used the default sink because no destination was available, the publish helper SHALL surface that warning clearly.

The publish helper SHALL NOT claim GUI visibility when the gateway reports default-sink routing or zero live delivery.

This fallback SHALL apply only to Houmao gateway publishing and SHALL NOT change the rule that third-party endpoints receive generated events for caller-managed delivery.

#### Scenario: Publish helper omits routing for gateway fallback
- **WHEN** an agent has rendered and validated a Houmao chart as standard AG-UI events
- **AND WHEN** the agent runs the Houmao gateway publish helper without `--thread-id`, `--run-id`, or `--connection-id`
- **THEN** the helper submits the event batch to the Houmao gateway for destination fallback routing
- **AND THEN** the helper reports the gateway publish result and warnings

#### Scenario: Explicit route still overrides fallback
- **WHEN** an agent passes `--thread-id agent-explicit-thread` to the publish helper
- **AND WHEN** the gateway has different last-sent and last-bound thread values
- **THEN** the helper sends the explicit thread route
- **AND THEN** it does not ask the gateway to infer the route from fallback state

#### Scenario: Default sink warning is shown
- **WHEN** an agent runs the publish helper without an explicit route
- **AND WHEN** the gateway reports default-sink routing due to no destination
- **THEN** the helper reports the default-sink warning
- **AND THEN** it does not describe the graphic as visible in the GUI

#### Scenario: Third-party endpoint behavior is unchanged
- **WHEN** an agent needs to send generated AG-UI events to a non-Houmao endpoint
- **THEN** `houmao-mgr` provides generated and validated event output
- **AND THEN** the Houmao gateway publish helper does not contact the non-Houmao endpoint or apply Houmao gateway fallback semantics to it
