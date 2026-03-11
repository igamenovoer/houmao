## MODIFIED Requirements

### Requirement: Demo packs have safe, explicit SKIP behavior

Each demo pack `run_demo.sh` SHALL exit with status code `0` and print a line
starting with `SKIP:` when a prerequisite is not met, including at least:

- missing credential profile inputs
- invalid/unauthorized credentials
- CAO connectivity unavailable
- `tmux` not available

Additionally, the demos that require local tmux + local filesystem effects (tmp
writes and `Esc` injection) SHALL SKIP unless `CAO_BASE_URL` is a supported
loopback CAO URL that uses `http`, host `localhost` or `127.0.0.1`, and an
explicit port.

#### Scenario: Remote CAO is skipped
- **WHEN** a developer runs the demo with `CAO_BASE_URL` set to a non-local URL
- **THEN** the demo exits `0` and prints `SKIP:` indicating local-only requirements

#### Scenario: Non-default loopback port is accepted
- **WHEN** a developer runs the demo with `CAO_BASE_URL=http://127.0.0.1:9991`
- **THEN** the demo treats that URL as satisfying the local-only CAO prerequisite
- **AND THEN** it does not skip solely because the loopback port is not `9889`
