# kimi-web-control Delta

## MODIFIED Requirements

### Requirement: An owned Kimi Web host supports gateway browser sign-in

The Kimi Web backend SHALL supply the owning gateway with a verified native browser destination using Kimi's token fragment. The destination SHALL use a qualified session path when the installed build supports it and use the verified native root when the browser must select the session in its UI.

#### Scenario: A fresh browser enters through the gateway

- **WHEN** an operator redeems a valid ticket for a supported live Kimi Web agent
- **THEN** the native UI uses its fragment authentication to open an authenticated browser session
- **AND THEN** the browser reaches the bound conversation through the qualified link or explicit native selection
- **AND THEN** Houmao's API binding remains independent of browser authentication

#### Scenario: Kimi host identity has changed

- **WHEN** listener, host, or conversation verification fails before the browser handoff
- **THEN** the backend withholds the private browser destination

#### Scenario: A fresh browser enters from an open gateway

- **WHEN** a clean browser opens the bare entry URL for a verified live Kimi Web agent with a valid empty roster
- **THEN** the gateway immediately redirects to Kimi's verified native browser destination
- **AND THEN** the native UI authenticates the browser and reaches the bound conversation by qualified link or native selection
