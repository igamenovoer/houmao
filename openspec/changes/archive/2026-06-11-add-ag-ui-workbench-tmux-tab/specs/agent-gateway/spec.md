## ADDED Requirements

### Requirement: Gateway maintains AG-UI destination fallback state
The gateway SHALL maintain volatile Houmao AG-UI destination fallback state containing last-bound-thread and last-sent-thread.

The last-bound-thread state SHALL start empty when the gateway process starts.

The last-sent-thread state SHALL start empty when the gateway process starts.

The gateway SHALL expose Houmao extension routes to read destination fallback state and to set and clear last-bound-thread.

The last-bound-thread set operation SHALL require a non-empty `threadId` string.

The last-sent-thread state SHALL be maintained by the gateway publish path rather than by workbench binding calls.

The destination fallback state SHALL be a Houmao gateway extension and SHALL NOT be described as part of the AG-UI core standard.

#### Scenario: Gateway starts with empty destination state
- **WHEN** a gateway process starts
- **THEN** last-bound-thread is empty
- **AND THEN** last-sent-thread is empty
- **AND THEN** reading destination fallback state reports no thread id for either field

#### Scenario: GUI binds a thread
- **WHEN** a workbench client sets last-bound-thread to `agent-1-thread`
- **THEN** the gateway stores `agent-1-thread` as the current bound AG-UI thread
- **AND THEN** later reads report a bound state for `agent-1-thread`

#### Scenario: GUI clears a thread binding
- **WHEN** the gateway has a last-bound-thread value
- **AND WHEN** a workbench client clears the binding
- **THEN** later reads report an empty last-bound-thread
- **AND THEN** last-sent-thread is not cleared by that workbench binding call

#### Scenario: Empty thread id is rejected
- **WHEN** a caller attempts to set last-bound-thread to an empty or blank string
- **THEN** the gateway rejects the request
- **AND THEN** the previous binding state is not replaced by a blank thread id

### Requirement: Gateway publish resolves destinations through message, last-sent, last-bound, then default sink
The gateway SHALL resolve AG-UI event publish routing in deterministic priority order.

Destination specified by the publish request or event batch SHALL take priority over gateway fallback state.

When no destination is specified by the publish request or event batch, the gateway SHALL use last-sent-thread if it exists.

When no destination is specified and last-sent-thread is empty, the gateway SHALL use last-bound-thread if it exists.

When no destination is specified and both last-sent-thread and last-bound-thread are empty, the gateway SHALL send the batch to a Houmao-defined default sink.

The default sink thread name SHALL NOT be returned as an agent-targetable route.

The current default sink behavior SHALL accept the valid batch, write a gateway log entry with safe routing metadata, perform no GUI fan-out, and return a warning that the default sink was used because no destination was available.

The gateway SHALL continue to validate event batches against standard AG-UI message/event rules before publishing them or sending them to the default sink.

The gateway SHALL NOT persist missed GUI events for replay because destination fallback or default sink routing was used.

#### Scenario: Message-specified destination wins
- **WHEN** a caller publishes an AG-UI event batch with an explicit `threadId`
- **AND WHEN** the gateway also has last-sent-thread and last-bound-thread values
- **THEN** the gateway routes the batch to the explicit thread id
- **AND THEN** it does not replace the route with fallback state

#### Scenario: Connection route is treated as message-specified
- **WHEN** a caller publishes an AG-UI event batch with `connectionId`
- **AND WHEN** the gateway can resolve that connection to a concrete thread
- **THEN** the gateway routes the batch to the explicit connection
- **AND THEN** the concrete thread for that connection is eligible to refresh last-sent-thread

#### Scenario: Event-level thread is treated as message-specified
- **WHEN** a caller publishes an AG-UI event batch without route fields on the publish request
- **AND WHEN** all events in the batch identify the same thread id through standard AG-UI event fields
- **THEN** the gateway routes the batch to that event-level thread id

#### Scenario: Publish uses last-sent thread before last-bound thread
- **WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **AND WHEN** last-sent-thread is `agent-last-sent-thread`
- **AND WHEN** last-bound-thread is `agent-last-bound-thread`
- **THEN** the gateway routes the batch to `agent-last-sent-thread`

#### Scenario: Publish uses bound thread when no sent thread exists
- **WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **AND WHEN** last-sent-thread is empty
- **AND WHEN** last-bound-thread is `agent-1-thread`
- **THEN** the gateway routes the batch to `agent-1-thread`
- **AND THEN** the publish response reports accepted and delivered counts according to live subscribers

#### Scenario: Publish falls through to default sink when no destination exists
- **WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **AND WHEN** last-sent-thread is empty
- **AND WHEN** last-bound-thread is empty
- **THEN** the gateway sends the batch to the default sink
- **AND THEN** the response includes a warning that the default sink was used because no destination was available
- **AND THEN** no GUI fan-out occurs

#### Scenario: Fallback publish remains live-only
- **WHEN** a caller publishes through last-sent-thread or last-bound-thread fallback
- **AND WHEN** no GUI stream is listening to that thread at publish time
- **THEN** the gateway reports zero live deliveries
- **AND THEN** the gateway does not store the batch for later GUI replay

### Requirement: Gateway refreshes last-sent AG-UI thread after concrete thread publishes
The gateway SHALL refresh last-sent-thread after an AG-UI publish resolves to a concrete non-sink thread destination and the gateway sends the batch through its normal publish path.

When a publish uses a message-specified thread destination, the gateway SHALL set last-sent-thread to that thread.

When a publish uses last-sent-thread fallback, the gateway SHALL refresh last-sent-thread with the same concrete thread and update its timestamp.

When a publish uses last-bound-thread fallback, the gateway SHALL set last-sent-thread to that bound thread after the publish is sent.

When a publish falls through to the default sink, the gateway SHALL NOT set last-sent-thread to the sink.

#### Scenario: Explicit thread publish refreshes last-sent
- **WHEN** a caller publishes a valid AG-UI event batch with `threadId = "agent-explicit-thread"`
- **THEN** the gateway routes the batch to `agent-explicit-thread`
- **AND THEN** last-sent-thread becomes `agent-explicit-thread`

#### Scenario: Bound-thread fallback refreshes last-sent
- **WHEN** last-sent-thread is empty
- **AND WHEN** last-bound-thread is `agent-bound-thread`
- **AND WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **THEN** the gateway routes the batch to `agent-bound-thread`
- **AND THEN** last-sent-thread becomes `agent-bound-thread`

#### Scenario: Default sink does not refresh last-sent
- **WHEN** last-sent-thread and last-bound-thread are empty
- **AND WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **THEN** the gateway uses the default sink
- **AND THEN** last-sent-thread remains empty
