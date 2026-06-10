## MODIFIED Requirements

### Requirement: Houmao gateway publish helper sends only standard AG-UI events to Houmao gateways
`houmao-mgr` SHALL provide a Houmao-gateway-specific AG-UI publish helper for sending caller-provided standard AG-UI events to a Houmao per-agent gateway ingestion route.

The publish helper SHALL validate the event sequence before sending it.

The publish helper SHALL NOT send Houmao typed component payloads directly unless they have first been rendered into standard AG-UI events.

The publish helper SHALL target Houmao gateway AG-UI ingestion semantics and SHALL NOT accept arbitrary third-party endpoint URLs, HTTP methods, content types, or endpoint-specific request policies.

For third-party AG-UI-compatible endpoints, `houmao-mgr` SHALL provide the generated and validated AG-UI event output, and the agent SHALL perform delivery outside the Houmao publish helper according to that endpoint's own constraints.

The publish helper SHALL fail before network submission when the input is not a valid AG-UI event sequence.

The publish helper SHALL report the Houmao gateway publish response, including accepted, stored, and delivered counts when the gateway returns them.

The publish helper SHALL identify Houmao gateway GUI-event publishing as live-only when `stored_count = 0` and replay support is absent.

The publish helper SHALL NOT claim durable delivery or GUI visibility when the gateway reports `delivered_count = 0`.

#### Scenario: Publish rejects typed payload before rendering
- **WHEN** an agent passes a raw `houmao.chart.bar` component payload to the publish helper as the event input
- **THEN** the command exits non-zero before contacting the Houmao gateway
- **AND THEN** the diagnostic tells the agent to render the component payload into AG-UI events first

#### Scenario: Publish sends validated AG-UI events to Houmao gateway
- **WHEN** an agent provides a valid AG-UI event sequence and a resolvable Houmao gateway target
- **THEN** the publish helper validates the events
- **AND THEN** it sends the events to the Houmao gateway AG-UI ingestion route
- **AND THEN** it reports the gateway response status without logging credential material

#### Scenario: Publish reports live-only no-subscriber result
- **WHEN** the Houmao gateway accepts a valid AG-UI event batch but no GUI stream receives it
- **THEN** the publish helper reports `accepted_count > 0`, `stored_count = 0`, and `delivered_count = 0`
- **AND THEN** it does not describe the message as visible in the GUI

#### Scenario: Third-party endpoint delivery stops at generated events
- **WHEN** an agent needs to send generated AG-UI events to a non-Houmao endpoint
- **THEN** `houmao-mgr` provides the generated and validated event payload
- **AND THEN** the Houmao publish helper does not contact the non-Houmao endpoint
