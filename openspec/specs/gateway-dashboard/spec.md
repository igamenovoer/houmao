# gateway-dashboard Specification

## Purpose

Provide a browser landing page for a live gateway so an operator can identify its managed agent, see availability, and use the existing native Web entry flow.

## Requirements

### Requirement: The gateway serves a public agent dashboard

The live gateway SHALL return a readable HTML dashboard at `GET /` without caller proof. It SHALL show the verified agent name or identifier, backend, run mode, gateway health, and native Web availability. Unknown runtime evidence SHALL be shown as unavailable.

#### Scenario: An operator opens the gateway base URL

- **WHEN** a browser requests `GET /` on a live gateway with a verified agent
- **THEN** the response is HTTP 200 HTML with the agent summary
- **AND THEN** the page distinguishes gateway health from native Web availability

#### Scenario: Runtime evidence is unavailable

- **WHEN** the gateway responds but cannot verify the current agent or its native surface
- **THEN** the page reports the unavailable details and withholds the Web entry action

### Requirement: The dashboard offers eligible native Web entry

The dashboard SHALL offer **Open agent Web UI** only for a verified available Web surface, a request eligible for owner-local Web entry, and available target Web entry policy. The action SHALL link to the bare `/v1/web/enter` path. When the action is unavailable, the page SHALL explain the reason.

#### Scenario: An operator opens an agent on an empty roster

- **WHEN** the operator selects the action for a live Web agent and the target has open gateway-admin permission for `web.enter` under a valid empty administrator roster
- **THEN** the existing entry handler redirects to the verified native interface

#### Scenario: An operator opens an agent with enrolled keys

- **WHEN** the operator selects the action for a live Web agent and its gateway has enrolled keys
- **THEN** the entry handler serves sign-in for callers with `web.enter` permission

#### Scenario: A busy Web agent remains reachable

- **WHEN** the verified native Web surface is available during a turn or human interaction
- **THEN** the action remains available on the eligible origin even when prompt admission is closed

#### Scenario: The selected agent runs in a non-Web mode

- **WHEN** the dashboard describes a headless, service, or TUI agent
- **THEN** it explains that the mode lacks a native Web interface and offers no entry link

#### Scenario: The operator visits through an advertised proxy

- **WHEN** the request fails the existing owner-local Web entry origin check
- **THEN** the dashboard provides owner-local connection guidance without offering a Web entry link

#### Scenario: The roster policy is unavailable

- **WHEN** the current target Web entry policy cannot be verified
- **THEN** the page reports that Web entry is unavailable and offers no entry link

### Requirement: Dashboard rendering is read-only and credential-free

The dashboard SHALL expose only the declared summary fields and static entry guidance. Rendering SHALL escape displayed values, avoid native sign-in lookup and ticket issuance, and leave runtime state untouched. The response SHALL use `Cache-Control: no-store` and `Referrer-Policy: no-referrer`.

#### Scenario: A caller views a dashboard on a keyed gateway

- **WHEN** an unsigned browser requests the dashboard
- **THEN** it receives the public summary without native URLs containing credentials, one-time tickets, or protected status details
- **AND THEN** subsequent protected operations still apply their own admission

#### Scenario: Native authority changes after the page renders

- **WHEN** a browser follows the action after the target policy, administrator roster, or native surface changes
- **THEN** the entry route applies current `web.enter` authority and native binding checks

### Requirement: The Dashboard Displays Public Roster Mode

The public dashboard SHALL show the selected gateway's open, keyed, or unavailable roster mode using the same verified evidence as endpoint discovery. Where Web entry is eligible, the dashboard SHALL explain direct entry or sign-in using that mode. Entry SHALL continue through the existing bare Web entry path and current admission checks.

#### Scenario: A browser opens the dashboard on a Web agent

- **WHEN** the dashboard can verify the current policy for an eligible Web surface
- **THEN** it shows open mode and direct-entry guidance for an empty roster, or keyed mode and sign-in guidance for a nonempty roster
- **AND THEN** the entry action still links to the bare `/v1/web/enter` path

#### Scenario: A browser opens a dashboard without eligible Web entry

- **WHEN** the dashboard describes a non-Web agent or a request that fails the existing entry eligibility checks
- **THEN** it can show the verified public roster mode alongside its existing unavailability guidance
- **AND THEN** it offers no new entry action

#### Scenario: The gateway cannot verify the current policy

- **WHEN** current policy evidence for the dashboard target is unavailable
- **THEN** the dashboard reports the roster mode as unavailable and withholds Web entry

#### Scenario: An unsigned browser reads the page on a keyed target

- **WHEN** the dashboard returns the public mode without caller proof
- **THEN** the page omits the default permission group, enrollment records, fingerprints, signer labels, keys, and tickets
- **AND THEN** following the entry action rechecks live eligibility and policy
