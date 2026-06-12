## ADDED Requirements

### Requirement: Tmux terminal panes synchronize measured size after attachment
Tmux panes SHALL distinguish the terminal size measured by xterm from the terminal size delivered to the active tmux attachment.

If a pane measures terminal columns and rows before the tmux attachment reaches the attached state, the pane SHALL deliver the current measured size to the runtime after attachment succeeds.

The pane SHALL continue to suppress redundant tmux resize actions when the current attachment has already received the measured columns and rows.

#### Scenario: Pre-attach fit is delivered after attach succeeds
- **WHEN** a tmux pane fits its xterm terminal while the attach WebSocket is still connecting
- **AND WHEN** the attach later succeeds without another browser layout change
- **THEN** the pane sends the current terminal columns and rows to the runtime attachment
- **AND THEN** the real tmux pane size matches the browser xterm size without requiring an outer browser-window resize

#### Scenario: Same-size refit does not spam resize
- **WHEN** a tmux pane has already delivered columns `100` and rows `29` to the current attachment
- **AND WHEN** Dockview or ResizeObserver triggers another fit that still reports columns `100` and rows `29`
- **THEN** the pane refreshes the visible terminal area
- **AND THEN** the pane does not dispatch another tmux resize action solely because the same-size fit ran

### Requirement: Tmux terminal panes handle host wheel repaint without stale edges
Tmux panes SHALL keep wheel scrolling inside the terminal host when a tmux terminal is attached.

Wheel scrolling inside the terminal host SHALL scroll the xterm viewport and schedule a full visible-row xterm refresh.

Wheel scrolling inside the terminal host SHALL NOT require resizing the browser window, Dockview panel, or terminal host before stale edge regions repaint.

The behavior SHALL NOT persist terminal bytes in reduced runtime state, browser storage, or AG-UI event caches.

#### Scenario: Host wheel scroll repaints real tmux attachment
- **WHEN** a tmux pane is attached to a real tmux session with enough output to scroll
- **AND WHEN** the tester scrolls inside the terminal host with the mouse wheel
- **THEN** the visible terminal area repaints across the terminal width without requiring a browser resize
- **AND THEN** terminal bytes are not written to reduced runtime state or localStorage

#### Scenario: Terminal wheel does not scroll outer workbench
- **WHEN** a tmux pane is attached and the pointer is over the terminal host
- **AND WHEN** the tester uses the mouse wheel
- **THEN** the scroll action is handled by the terminal viewport
- **AND THEN** the surrounding workbench layout does not move because of that terminal wheel event

### Requirement: Workbench validation covers fresh-agent first-connect graphics
The workbench validation suite SHALL include a real-agent smoke path that launches or relaunches a Houmao agent into a clean browser session, connects once, sends one graphics-producing prompt, and verifies visible template graphics without requiring a disconnect and reconnect.

The smoke assertion SHALL treat one Plotly chart with multiple SVG layers as one visible chart.

The smoke evidence SHALL include enough information to distinguish a rendering failure, a publish-delivery failure, an active-thread routing failure, and a test-locator failure.

#### Scenario: Fresh agent renders graphics on first connect
- **WHEN** the real-agent smoke starts a clean browser session and starts a new or freshly relaunched Houmao agent
- **AND WHEN** the tester connects the workbench pane to that agent exactly once
- **AND WHEN** the tester sends a prompt that publishes one Houmao template graphic
- **THEN** the workbench displays the template graphic without requiring disconnect or reconnect
- **AND THEN** the smoke evidence records the thread id, prompt nonce, chart title, and any visible errors

#### Scenario: Plotly multi-SVG chart passes visible assertion
- **WHEN** the real-agent smoke receives a Plotly-rendered template graphic
- **AND WHEN** the rendered chart contains multiple SVG elements for layers or axes
- **THEN** the smoke treats the chart as visible when at least one chart SVG layer is visible inside the template chart container
- **AND THEN** the smoke does not fail only because the chart contains more than one SVG element
