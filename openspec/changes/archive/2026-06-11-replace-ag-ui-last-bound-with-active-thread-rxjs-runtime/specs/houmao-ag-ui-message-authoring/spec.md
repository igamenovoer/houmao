## ADDED Requirements

### Requirement: Houmao gateway publish helper can rely on active-thread fallback
The Houmao AG-UI publish helper SHALL allow callers to omit explicit AG-UI routing when targeting a Houmao gateway.

When explicit routing is omitted, the publish helper SHALL submit the validated AG-UI event batch to the Houmao gateway in a form that allows active-thread fallback routing.

Explicit `connectionId`, `threadId`, or `runId` options SHALL remain available and SHALL take priority over active-thread and default sink fallback.

When the gateway routes through active-thread, the publish helper SHALL report the gateway publish result, including accepted and delivered counts.

When the gateway reports that it used the default sink because no destination was available, the publish helper SHALL surface that warning clearly.

The publish helper SHALL NOT claim GUI visibility when the gateway reports default-sink routing or zero live delivery.

The publish helper SHALL NOT describe last-sent-thread as a fallback route.

#### Scenario: Publish helper omits routing for active-thread fallback
- **WHEN** an agent has rendered and validated a Houmao chart as standard AG-UI events
- **AND WHEN** the agent runs the Houmao gateway publish helper without `--thread-id`, `--run-id`, or `--connection-id`
- **THEN** the helper submits the event batch to the Houmao gateway for active-thread fallback routing
- **AND THEN** the helper reports the gateway publish result and warnings

#### Scenario: Explicit route still overrides active-thread fallback
- **WHEN** an agent passes `--thread-id agent-explicit-thread` to the publish helper
- **AND WHEN** the gateway has a different active-thread value
- **THEN** the helper sends the explicit thread route
- **AND THEN** it does not ask the gateway to infer the route from active-thread

#### Scenario: Default sink warning is shown for missing active thread
- **WHEN** an agent runs the publish helper without an explicit route
- **AND WHEN** the gateway reports default-sink routing due to no active-thread destination
- **THEN** the helper reports the default-sink warning
- **AND THEN** it does not describe the graphic as visible in the GUI

#### Scenario: Last-sent bookkeeping is not described as fallback
- **WHEN** publish helper documentation or output describes omitted routing
- **THEN** it lists active-thread fallback and default sink behavior
- **AND THEN** it does not list last-sent-thread as a fallback destination

