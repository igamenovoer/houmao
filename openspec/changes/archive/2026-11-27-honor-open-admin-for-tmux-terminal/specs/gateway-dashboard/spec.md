# Spec Delta

## MODIFIED Requirements

### Requirement: The dashboard offers eligible browser terminal entry

The dashboard SHALL evaluate browser terminal eligibility independently from native Web entry. For an eligible owner-local request and live tmux binding, it SHALL link **View tmux terminal** to `/v1/terminal/view`. An open or keyed roster SHALL also offer **Interact with tmux** at `/v1/admin/terminal/attach`. The action SHALL present direct entry for open mode and administrator sign-in for keyed mode. It SHALL label supervisor consoles for modes backed by supervision.

#### Scenario: A Web agent has both surfaces

- **WHEN** the dashboard serves an eligible local request for a Web agent with a verified native Web surface and a live tmux supervisor
- **THEN** the native Web and tmux view actions appear independently
- **AND THEN** the tmux action identifies the supervisor console

#### Scenario: The roster is empty

- **WHEN** the gateway verifies an empty roster and has an eligible tmux session
- **THEN** the dashboard offers both view and interactive entry
- **AND THEN** following the bare interactive link opens the terminal without an administrator login while the roster remains open

#### Scenario: The roster has enrolled administrator keys

- **WHEN** the gateway verifies a keyed roster and has an eligible tmux session
- **THEN** the dashboard offers both view and interactive entry
- **AND THEN** following the bare interactive link offers administrator sign-in before attaching

#### Scenario: Administrator policy is unavailable

- **WHEN** the gateway cannot verify its roster but can verify a live tmux binding on the owner-local origin
- **THEN** the dashboard offers the anonymous view and withholds the admin action

#### Scenario: The binding or connection is ineligible

- **WHEN** the tmux session cannot be verified or the request uses advertised proxy ingress
- **THEN** the dashboard withholds terminal actions and displays a safe reason

#### Scenario: An operator follows a link after the agent changes

- **WHEN** the operator requests the selected terminal mode after the dashboard was rendered
- **THEN** the gateway checks the current terminal authority and the permission for that mode before granting access
