## ADDED Requirements

### Requirement: CLI reference documents tmux-session targeting for `agents gateway`
The CLI reference pages `docs/reference/cli/agents-gateway.md` and `docs/reference/cli.md` SHALL document `--target-tmux-session <tmux-session-name>` as an explicit selector for single-target `houmao-mgr agents gateway ...` commands.

That documentation SHALL describe the selector as mutually exclusive with `--agent-id`, `--agent-name`, and `--current-session`. It SHALL also document `--pair-port` as the pair-authority override name for explicit `--agent-id` and `--agent-name` targeting.

The docs SHALL state that `--pair-port` is unsupported with tmux-session targeting because the command follows the addressed session's manifest-declared authority after local resolution. They SHALL also explain that `--pair-port` is not the same thing as a gateway listener port override such as lower-level `--gateway-port`.

The `agents-gateway` reference SHALL distinguish outside-tmux `--target-tmux-session` targeting from inside-tmux current-session targeting and SHALL explain when each mode is appropriate.

#### Scenario: CLI reference page lists the tmux-session selector and targeting boundary
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** the option tables include `--target-tmux-session`
- **AND THEN** the page explains that `--target-tmux-session` is for explicit outside-tmux targeting while `--current-session` is for the owning tmux session

#### Scenario: Top-level CLI guidance explains the port rule for tmux-session targeting
- **WHEN** a reader checks `docs/reference/cli.md` for gateway targeting rules
- **THEN** the page explains that `--pair-port` remains supported with `--agent-id` or `--agent-name`
- **AND THEN** the page explains that `--pair-port` is rejected with `--target-tmux-session` because tmux-session targeting follows manifest-declared authority

#### Scenario: Gateway CLI reference distinguishes pair-authority port from gateway listener port
- **WHEN** a reader opens `docs/reference/cli/agents-gateway.md`
- **THEN** the page explains that `--pair-port` selects the Houmao pair authority
- **AND THEN** the page does not imply that `--pair-port` controls the live gateway listener port
