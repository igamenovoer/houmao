## ADDED Requirements

### Requirement: Gateway maintains active-thread destination state
The gateway SHALL maintain volatile Houmao AG-UI destination state containing active-thread and last-sent-thread.

The active-thread state SHALL start empty when the gateway process starts.

The last-sent-thread state SHALL start empty when the gateway process starts.

The gateway SHALL expose Houmao extension routes to read destination state, read active-thread, set active-thread, and clear active-thread.

The active-thread set operation SHALL require a non-empty `threadId` string.

The destination state SHALL be a Houmao gateway extension and SHALL NOT be described as part of the AG-UI core standard.

#### Scenario: Gateway starts with empty active destination state
- **WHEN** a gateway process starts
- **THEN** active-thread is empty
- **AND THEN** last-sent-thread is empty

#### Scenario: GUI sets active thread
- **WHEN** a workbench client sets active-thread to `agent-1-thread`
- **THEN** the gateway stores `agent-1-thread` as the current active AG-UI thread
- **AND THEN** later reads report active state for `agent-1-thread`

#### Scenario: Empty active thread is rejected
- **WHEN** a caller attempts to set active-thread to an empty or blank string
- **THEN** the gateway rejects the request
- **AND THEN** the previous active-thread state is not replaced by a blank value

### Requirement: Gateway conditionally clears active-thread
The gateway SHALL support clearing active-thread.

When a clear request includes an expected thread id, the gateway SHALL clear active-thread only if the current active-thread matches that expected thread id.

When a clear request includes an expected thread id that does not match the current active-thread, the gateway SHALL leave active-thread unchanged and return the current active-thread state.

Clearing active-thread SHALL NOT clear last-sent-thread.

#### Scenario: Matching expected thread clears active state
- **WHEN** active-thread is `alpha-thread`
- **AND WHEN** a caller clears active-thread with expected thread id `alpha-thread`
- **THEN** the gateway clears active-thread
- **AND THEN** last-sent-thread is unchanged

#### Scenario: Stale expected thread does not clear active state
- **WHEN** active-thread is `beta-thread`
- **AND WHEN** a stale caller clears active-thread with expected thread id `alpha-thread`
- **THEN** the gateway keeps active-thread set to `beta-thread`

### Requirement: Gateway publish resolves destinations through explicit route, active-thread, then default sink
The gateway SHALL resolve AG-UI event publish routing in deterministic priority order.

Destination specified by the publish request or event batch SHALL take priority over gateway fallback state.

When no destination is specified by the publish request or event batch, the gateway SHALL use active-thread if it exists.

When no destination is specified and active-thread is empty, the gateway SHALL send the batch to a Houmao-defined default sink.

The gateway SHALL NOT use last-sent-thread as a publish fallback destination.

The default sink thread name SHALL NOT be returned as an agent-targetable route.

The current default sink behavior SHALL accept the valid batch, write a gateway log entry with safe routing metadata, perform no GUI fan-out, and return a warning that the default sink was used because no destination was available.

#### Scenario: Explicit thread destination wins over active thread
- **WHEN** a caller publishes an AG-UI event batch with an explicit `threadId`
- **AND WHEN** the gateway has a different active-thread value
- **THEN** the gateway routes the batch to the explicit thread id

#### Scenario: Active thread is used for omitted route
- **WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **AND WHEN** active-thread is `agent-active-thread`
- **THEN** the gateway routes the batch to `agent-active-thread`
- **AND THEN** the publish response reports accepted and delivered counts according to live subscribers

#### Scenario: Last-sent thread is not used as fallback
- **WHEN** active-thread is empty
- **AND WHEN** last-sent-thread is `agent-last-sent-thread`
- **AND WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **THEN** the gateway sends the batch to the default sink

#### Scenario: Default sink is used when active thread is empty
- **WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **AND WHEN** active-thread is empty
- **THEN** the gateway sends the batch to the default sink
- **AND THEN** the response includes a warning that no destination was available

### Requirement: Gateway keeps last-sent-thread as bookkeeping only
The gateway SHALL refresh last-sent-thread after an AG-UI publish resolves to a concrete non-sink destination and the gateway sends the batch through its normal publish path.

When a publish uses a message-specified destination, the gateway SHALL set last-sent-thread to that concrete destination when known.

When a publish uses active-thread fallback, the gateway SHALL set last-sent-thread to that active thread after the publish is sent.

When a publish falls through to the default sink, the gateway SHALL NOT set last-sent-thread to the sink.

Last-sent-thread SHALL NOT participate in future destination fallback decisions.

#### Scenario: Active-thread publish refreshes last-sent
- **WHEN** active-thread is `agent-active-thread`
- **AND WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **THEN** the gateway routes the batch to `agent-active-thread`
- **AND THEN** last-sent-thread becomes `agent-active-thread`

#### Scenario: Default sink does not refresh last-sent
- **WHEN** active-thread is empty
- **AND WHEN** a caller publishes a valid AG-UI event batch without a message-specified destination
- **THEN** the gateway uses the default sink
- **AND THEN** last-sent-thread remains unchanged

