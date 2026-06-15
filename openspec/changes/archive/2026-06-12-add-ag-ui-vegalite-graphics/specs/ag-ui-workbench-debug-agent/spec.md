## ADDED Requirements

### Requirement: Debug Agent supports Vega-Lite typed component payloads
The Debug Agent sender SHALL include `houmao.graphic.vegalite` in its typed component lane.

The typed component lane SHALL validate or wrap a valid Vega-Lite payload into standard AG-UI tool-call events before delivering it to the Debug Agent display.

The Debug Agent display SHALL render `houmao.graphic.vegalite` through the same Layer 2 renderer path used by ordinary workbench panes.

#### Scenario: Sender publishes a Vega-Lite payload
- **WHEN** a user selects `houmao.graphic.vegalite` in the Debug Agent typed component sender
- **AND WHEN** the user sends a valid inline Vega-Lite payload
- **THEN** the display receives a complete AG-UI tool-call event sequence
- **AND THEN** the display renders the Vega-Lite chart graphically

#### Scenario: Sender surfaces Vega-Lite validation failure
- **WHEN** a user enters a `houmao.graphic.vegalite` payload with remote `data.url`
- **AND WHEN** the user validates or sends the payload
- **THEN** the sender shows a deterministic validation failure
- **AND THEN** the invalid payload is not delivered as a successful rendered component

### Requirement: Debug Agent fixtures cover Vega-Lite rendering and fallback
The repository SHALL include deterministic Debug Agent fixtures or tests that prove external AG-UI event publishing can render a valid Vega-Lite chart and can show a visible fallback for a malformed Vega-Lite spec.

#### Scenario: E2E posts Vega-Lite chart events
- **WHEN** the Playwright test opens the workbench and creates a Debug Agent pane
- **AND WHEN** the test posts a valid `houmao.graphic.vegalite` AG-UI event batch to the debug relay events endpoint
- **THEN** the publish response reports accepted events and at least one live delivery
- **AND THEN** the Debug Agent display shows a visible Vega-Lite chart

#### Scenario: E2E posts malformed Vega-Lite events
- **WHEN** the Playwright test posts a malformed `houmao.graphic.vegalite` AG-UI event batch to a connected Debug Agent display
- **THEN** the display shows an invalid component fallback
- **AND THEN** the workbench remains responsive for later valid events
