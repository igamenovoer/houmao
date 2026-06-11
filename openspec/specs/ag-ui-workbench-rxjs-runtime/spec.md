# ag-ui-workbench-rxjs-runtime Specification

## Purpose
Define the AG-UI workbench browser runtime event layer, RxJS action/effect/state patterns, shared polling, cancellation, and React integration boundaries.

## Requirements
### Requirement: Workbench has an RxJS runtime event layer
The AG-UI workbench SHALL use RxJS as the primary browser runtime event facility for long-lived asynchronous workflows.

The runtime SHALL expose a typed action dispatch surface, a shared observable state surface, runtime effects, and React selector hooks.

The runtime SHALL own cross-pane workflows, including active-thread polling, active-thread mutation, watched-target lifecycle, AG-UI stream lifecycle, tmux bridge lifecycle, and storage side effects as those workflows migrate into the runtime.

React components SHALL render runtime-derived view models and dispatch runtime actions rather than owning cross-pane long-lived workflows directly.

#### Scenario: Runtime exposes state through React selectors
- **WHEN** a React pane needs runtime state such as active-thread status or watched-target runtime state
- **THEN** the pane subscribes through a runtime selector hook
- **AND THEN** the pane does not subscribe directly to raw internal subjects

#### Scenario: Runtime accepts typed UI actions
- **WHEN** a user clicks a pane control that affects cross-pane state
- **THEN** the component dispatches a typed runtime action
- **AND THEN** runtime effects perform any required network, cache, timer, or cancellation work

### Requirement: Runtime effects are cancellable and lifecycle-owned
The RxJS runtime SHALL model long-lived workflows as cancellable effects.

Runtime effects SHALL stop their timers, HTTP streams, WebSocket streams, and cache writes when the owning pane, watched target, gateway subscription, or runtime is removed.

Runtime effects SHALL use deterministic teardown boundaries rather than relying on orphaned component-local refs.

#### Scenario: Pane close cancels pane-owned effects
- **WHEN** a pane with a live AG-UI stream or tmux attachment is closed
- **THEN** the runtime stops the stream or attachment effect for that pane
- **AND THEN** later stream events do not mutate removed pane state

#### Scenario: Runtime teardown stops periodic effects
- **WHEN** the workbench runtime is disposed during page unload or test teardown
- **THEN** active polling, reconnect timers, HTTP streams, WebSocket streams, and pending cache effects are stopped

### Requirement: Runtime shares gateway polling by gateway key
The RxJS runtime SHALL maintain at most one active-thread polling effect per normalized Houmao gateway key.

The active-thread polling effect SHALL start when at least one eligible pane is interested in that gateway and SHALL stop when no pane remains interested, when the runtime is disposed, or when the gateway is classified as active-thread unsupported.

The default active-thread polling interval SHALL be 1 second.

The active-thread polling effect SHALL avoid overlapping requests for the same gateway key.

The active-thread polling effect SHALL NOT abort an in-flight active-thread request solely because the next interval tick arrives.

The active-thread polling effect SHALL route deterministic unsupported-route responses, such as `404` or `405`, to unsupported state rather than retrying indefinitely as transient errors.

#### Scenario: Multiple panes share one active-thread poller
- **WHEN** two panes target the same Houmao gateway
- **THEN** the runtime uses one active-thread poller for that gateway
- **AND THEN** both panes derive their active indicator state from that shared poll result

#### Scenario: Poller stops when no pane is interested
- **WHEN** the last pane interested in a gateway closes or retargets away
- **THEN** the runtime stops that gateway's active-thread poller

#### Scenario: Poller stops when gateway is unsupported
- **WHEN** the active-thread poller receives a deterministic unsupported-route response for a gateway
- **THEN** the runtime dispatches unsupported active-thread state for that gateway
- **AND THEN** the runtime stops that gateway's active-thread poller until a new gateway lifecycle is registered

#### Scenario: Slow poll is not aborted by interval tick
- **WHEN** an active-thread request remains in flight when the next poll interval tick occurs
- **THEN** the runtime does not abort that in-flight request solely because of the tick
- **AND THEN** the runtime applies the eventual success or failure result from the in-flight request

### Requirement: Runtime avoids raw stream replay buffers by default
The RxJS runtime SHALL NOT use unbounded replay buffers for raw AG-UI events, raw tmux terminal bytes, WebSocket payloads, prompt text, request bodies, forwarded props, credentials, cookies, bearer tokens, or authorization headers.

The runtime SHALL store stream content only through explicit reduced state or existing watched-target event cache boundaries.

The runtime SHALL NOT persist raw tmux terminal bytes in localStorage or IndexedDB.

#### Scenario: Raw terminal bytes are not replayed by runtime subjects
- **WHEN** a tmux attachment receives terminal output
- **THEN** the runtime does not expose that output through a replayed subject or persisted runtime snapshot
- **AND THEN** a later pane subscription cannot recover prior terminal output from the runtime

#### Scenario: AG-UI event persistence remains explicit
- **WHEN** an AG-UI stream receives events for an unwatched pane
- **THEN** the runtime may reduce those events into current visible pane state
- **AND THEN** it does not persist those events to the watched-target cache unless the target is watched

### Requirement: Pure AG-UI reducers remain separate from runtime effects
The RxJS runtime SHALL feed AG-UI events into pure reducer functions for visible state updates.

Runtime effects SHALL NOT mix protocol parsing, network lifecycle, and component rendering logic into one monolithic effect.

#### Scenario: AG-UI event updates use pure reducers
- **WHEN** an AG-UI stream emits a valid event
- **THEN** the runtime routes that event through the existing AG-UI event reducer or an equivalent pure reducer
- **AND THEN** the resulting state can be unit-tested without opening a network stream
