## ADDED Requirements

### Requirement: README mentions system-skill help
The `README.md` system-skills guidance SHALL tell users that each current installed Houmao system skill supports an explicit help request.

The README SHALL describe help as a read-only way to learn what a skill can do before asking it to perform a workflow.

The README SHALL include at least one example prompt such as `$houmao-touring help` or `$houmao-agent-email-comms help`.

The README SHALL preserve the distinction between skill-level help and the `houmao-mgr system-skills install` CLI surface.

#### Scenario: Reader discovers skill help from README
- **WHEN** a reader scans the README system-skill guidance
- **THEN** they see that installed Houmao system skills can answer explicit help requests
- **AND THEN** they see an example of asking one skill for help
- **AND THEN** the README does not imply that help runs commands or mutates Houmao state
