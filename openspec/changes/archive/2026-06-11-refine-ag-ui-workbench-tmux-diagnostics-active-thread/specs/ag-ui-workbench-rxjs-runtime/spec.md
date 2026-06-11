## MODIFIED Requirements

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
