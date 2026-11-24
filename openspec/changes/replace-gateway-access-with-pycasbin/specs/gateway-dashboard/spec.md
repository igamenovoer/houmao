# Spec Delta

## MODIFIED Requirements

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
