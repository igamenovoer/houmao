## ADDED Requirements

### Requirement: CLI reference documents external managed-agent imports
The CLI reference SHALL document the `houmao-mgr agents external` command family for registering and managing communication-only external Houmao agents.

At minimum, the reference SHALL cover:
- `agents external register`,
- `agents external list`,
- `agents external get`,
- `agents external verify`,
- `agents external remove`,
- the required registration inputs `--name`, `--api-base-url`, and `--agent-ref`,
- gateway expectation flags,
- local selector behavior after registration,
- the distinction between local lifecycle-managed agents and external communication-only imports.

The CLI reference SHALL identify which normal `houmao-mgr agents` commands are supported for external targets and which lifecycle or raw local-control commands are rejected.

The CLI reference SHALL include security guidance stating that remote passive-server URLs should be exposed only through a trusted channel such as SSH forwarding, VPN, Tailscale, or a secured reverse proxy until an authenticated remote transport is available.

#### Scenario: Reader can register a remote Houmao agent from CLI docs
- **WHEN** a reader looks up `houmao-mgr agents external`
- **THEN** the CLI reference shows the registration command form with `--name`, `--api-base-url`, and `--agent-ref`
- **AND THEN** it explains that the remote URL must be a reachable maintained `houmao-passive-server`

#### Scenario: Reader sees supported external target operations
- **WHEN** a reader checks external-agent command support in the CLI reference
- **THEN** the page lists communication-safe commands such as list, state, prompt, interrupt, gateway status, gateway prompt, and supported pair-backed mail operations
- **AND THEN** it lists rejected local lifecycle or raw local-control operations such as stop, relaunch, cleanup, gateway attach, gateway detach, and gateway send-keys

#### Scenario: Reader sees secure exposure guidance
- **WHEN** a reader copies an example using `--api-base-url`
- **THEN** the surrounding documentation warns against exposing an unauthenticated passive-server on a public network
- **AND THEN** it recommends trusted-channel deployment options for remote access
