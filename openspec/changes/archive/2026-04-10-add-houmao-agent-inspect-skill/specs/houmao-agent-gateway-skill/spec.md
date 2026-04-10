## ADDED Requirements

### Requirement: `houmao-agent-gateway` delegates generic managed-agent inspection to `houmao-agent-inspect`
The packaged `houmao-agent-gateway` skill SHALL treat generic requests to inspect managed-agent liveness, tmux backing, mailbox posture, runtime artifacts, or non-gateway logs as outside its primary ownership unless that inspection is specifically about gateway lifecycle, gateway-only control, reminder state, or mail-notifier state.

For those generic managed-agent inspection requests, the packaged skill SHALL direct the caller to `houmao-agent-inspect`.

The packaged skill MAY continue using gateway status and gateway-owned TUI tracker surfaces when the inspection target is explicitly gateway-specific.

#### Scenario: Generic managed-agent inspection routes to the inspect skill
- **WHEN** a caller asks the gateway skill to inspect a managed agent broadly rather than to inspect the gateway lifecycle or gateway-only services specifically
- **THEN** the skill directs the caller to `houmao-agent-inspect`
- **AND THEN** it does not present the gateway skill as the canonical owner of generic managed-agent inspection

#### Scenario: Gateway-specific inspection remains on the gateway skill
- **WHEN** a caller asks to inspect live gateway status, raw gateway-owned TUI tracker state, reminder state, or notifier state
- **THEN** the skill continues directing the caller to the supported gateway surfaces
- **AND THEN** it does not require a handoff to `houmao-agent-inspect` for that gateway-specific inspection work
