# Spec Delta

## MODIFIED Requirements

### Requirement: Fixture qualification records actual evidence and limitations

Qualification SHALL record actual client version/build, model, protocol, case, native surface, and outcome without credentials. DeepSeek SHALL be exercised for every supported client/mode pair, including DSH ACP headless and interactive Web. The three terminal clients retain their headless and TUI lanes. Self-hosted live qualification SHALL use an explicitly configured model other than Qwen3.8 when available; unavailable prerequisites SHALL be reported without a success claim.

#### Scenario: Self-hosted endpoint is not configured
- **WHEN** live qualification has no configured compatible self-hosted endpoint/model
- **THEN** its report marks those live lanes as not run with the missing prerequisite
- **AND THEN** passing hermetic tests do not become a live qualification claim

#### Scenario: Historical capture records Qwen usage
- **WHEN** an existing sanitized accounting fixture records an earlier Qwen capture
- **THEN** it retains its factual model/version metadata
- **AND THEN** maintained launch helpers do not depend on the historical change-local wrapper

#### Scenario: DSH Headless Qualification Does Not Imply Interactive Support
- **WHEN** a DSH ACP cloud smoke passes
- **THEN** its report records headless ACP as the qualified control surface
- **AND THEN** Claude, Codex, and Kimi retain their required headless and unattended TUI lanes

#### Scenario: DSH TUI Qualification Uses the Native Web Surface
- **WHEN** a DSH fixture selects `mode=tui`
- **THEN** qualification launches its Web Host and records Web API and browser evidence
- **AND THEN** a tmux log capture or passing ACP run does not qualify the interactive lane


## ADDED Requirements

### Requirement: DSH Web Fixtures Share the Existing Generic Endpoint Cases

DSH `tui` fixture preparation SHALL reuse the `self-hosted` and `cloud-api` cases, explicit model/protocol inputs, and private credential/run roots established for headless DSH. Raw and managed preparation SHALL expose the same native Web behavior. Browser startup and connection credentials SHALL remain controlled locally without entering tracked reports.

#### Scenario: A Fresh Host Uses Cloud DSH Interactively
- **WHEN** a developer configures only the selected DeepSeek key, endpoint, and model
- **THEN** a DSH Web test agent can be prepared without a self-hosted model, auth JSON, or desktop display

#### Scenario: A Browser Connects to the Managed Fixture
- **WHEN** a qualification browser signs in through the fixture's private local connection mechanism
- **THEN** it opens the same native session targeted by the programmatic adapter
- **AND THEN** public fixture summaries contain only non-secret location and identity metadata

### Requirement: DSH Web Qualification Exercises Mixed Control and Admission Races

Qualification SHALL exercise actual browser and API clients on the same native session, including human/program prompts, progress, human questions, interruption, readiness races, restart, and usage. Deterministic coverage SHALL use controlled models/processes and synthetic credentials. Live provider qualification SHALL record actual evidence separately.

#### Scenario: Browser and Program Both Drive the Session
- **WHEN** a browser submits work, the API observes it, and a later API prompt is submitted
- **THEN** both clients observe one native history with correct terminal outcomes

#### Scenario: Browser Input Races Ordinary Programmatic Delivery
- **WHEN** a controlled test starts human work after API readiness inspection but before native admission
- **THEN** the ordinary API attempt is refused and never appears in the native inbox after the human turn ends

#### Scenario: Restart Follows Uncertain Admission
- **WHEN** the qualification host dies or loses its response after native admission
- **THEN** the attempt reports failure or uncertainty and explicit recovery does not replay its input

#### Scenario: No Real Account Exists in CI
- **WHEN** hermetic Web qualification runs without developer credentials
- **THEN** browser/API coexistence and lifecycle behavior are tested using controlled endpoints without paid provider calls
