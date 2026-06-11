## ADDED Requirements

### Requirement: Real workbench smoke exercises a live agent GUI graphics loop
Houmao SHALL provide an explicit opt-in smoke that drives the AG-UI workbench GUI against one existing real managed Houmao test agent.

The smoke SHALL restart the selected test agent before exercising the GUI path.

The smoke SHALL use passive-server discovery or resolution to select the target agent in the workbench.

The smoke SHALL connect the workbench pane to the selected agent gateway before submitting a prompt.

The smoke SHALL submit the validation prompt through the workbench prompt composer and run button rather than by posting directly to the gateway from the test harness.

The validation prompt SHALL ask the agent to publish one `houmao.graphic.template` chart to the current GUI thread and request a nonce-labeled text completion marker.

The smoke SHALL remain opt-in and SHALL NOT be part of the default unit-test command.

#### Scenario: Operator enables the real-agent GUI smoke
- **WHEN** an operator runs the real-agent GUI smoke with the required opt-in flag, passive-server URL, and test-agent selector
- **THEN** the smoke restarts the selected managed agent through maintained `houmao-mgr` lifecycle commands
- **AND THEN** the smoke opens the AG-UI workbench in Playwright
- **AND THEN** the smoke selects the same agent through the workbench agent picker
- **AND THEN** the smoke connects the workbench pane to the agent gateway before sending the prompt

#### Scenario: Missing prerequisites fail before model work
- **WHEN** the opt-in flag, passive-server URL, test-agent selector, live gateway, or Playwright browser prerequisite is missing
- **THEN** the smoke fails or skips with a diagnostic naming the missing prerequisite
- **AND THEN** the smoke does not submit a model prompt

### Requirement: Real workbench smoke validates rendered template graphics
The real-agent GUI smoke SHALL verify that the selected agent and gateway advertise AG-UI run submission, GUI connect streams, and live published-event fanout before submitting the validation prompt.

The smoke SHALL verify local `houmao.graphic.template` authoring support before submitting the validation prompt.

The smoke SHALL record template graphics presentation metadata when the gateway advertises it, but SHALL NOT require `generatedGraphics=true` for TUI-backed agents that publish already-rendered AG-UI events through `/v1/ag-ui/events`.

The validation prompt SHALL include a unique nonce, the current GUI thread id when available, the `houmao.graphic.template` component name, the requested `vega-lite` renderer preference, and a simple chart data set.

The smoke SHALL pass only when the workbench DOM contains the nonce-labeled chart title and visible renderer output.

The smoke SHALL record whether the workbench transcript contains the nonce-labeled completion marker when the agent emits one, but the completion marker SHALL NOT be required when the nonce-labeled chart is rendered.

The smoke SHALL prefer visible Vega-Lite SVG evidence for the chart renderer.

The smoke SHALL treat a text-only answer, Markdown-only chart, stale chart, wrong component name, or missing rendered chart as a failure.

#### Scenario: Agent publishes and GUI renders a template graphic
- **WHEN** the connected workbench pane submits the validation prompt to the selected real agent
- **AND WHEN** the agent publishes a complete `houmao.graphic.template` AG-UI tool-call sequence for the prompt nonce
- **THEN** the workbench displays the prompt-specific chart title
- **AND THEN** the workbench displays visible chart renderer output for that tool call
- **AND THEN** the smoke records whether the transcript contains the prompt-specific completion marker

#### Scenario: Text-only completion does not satisfy graphics smoke
- **WHEN** the connected workbench pane receives the prompt-specific completion marker but no `houmao.graphic.template` chart with the prompt-specific title
- **THEN** the smoke fails
- **AND THEN** the failure diagnostic distinguishes missing rendered graphics from optional missing text completion

### Requirement: Real workbench smoke records actionable failure evidence
The real-agent GUI smoke SHALL record diagnostics for setup, agent, gateway, and browser failures.

Failure evidence SHALL include the selected agent id or name, passive-server URL, resolved gateway target, GUI thread id when available, AG-UI capabilities response when available, submitted prompt, browser console output, screenshot, and visible transcript text.

When raw AG-UI events or reconstructed tool-call diagnostics are available through the workbench or gateway, the smoke SHALL preserve them as additional evidence.

The smoke SHALL detach or close GUI browser resources during cleanup. It SHALL NOT stop, restart again, shut down, or interrupt the selected managed agent after the smoke unless the operator enables an explicit cleanup option.

#### Scenario: Graphics assertion failure saves diagnostics
- **WHEN** the real-agent GUI smoke does not observe the expected rendered chart before the timeout
- **THEN** the smoke saves browser and gateway diagnostics sufficient to tell whether selection, connection, prompt submission, agent output, event delivery, or rendering failed
- **AND THEN** the smoke exits non-zero or reports a clear skipped status according to the missing prerequisite

#### Scenario: Cleanup preserves existing test agent ownership
- **WHEN** the real-agent GUI smoke completes or fails after relaunching an existing selected test agent
- **THEN** the smoke closes browser resources and detaches GUI subscriptions it opened
- **AND THEN** the smoke leaves the managed agent running unless an explicit stop-after-smoke option is enabled
