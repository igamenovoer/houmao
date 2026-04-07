## Why

The packaged system-skill specs drifted from the current mailbox skill boundary after `houmao-agent-messaging` was tightened into a communication router that only discovers mailbox posture and hands mailbox work to the dedicated mailbox skills. The main specs still describe `houmao-agent-messaging` as if it directly owns ordinary mailbox operations, and one synced gateway spec still names retired split mailbox skills.

## What Changes

- Update the `houmao-agent-messaging` spec so mailbox behavior is defined as discovery plus handoff, not direct ownership of ordinary mailbox commands and routes.
- Update the `houmao-agent-gateway` spec so its mailbox delegation points at `houmao-agent-email-comms` and `houmao-process-emails-via-gateway` instead of retired split mailbox skills.
- Update the system-skills CLI-reference spec so docs describe `houmao-agent-messaging` as the mailbox routing entrypoint and `houmao-agent-email-comms` as the ordinary mailbox operations skill.
- Update the README system-skills spec so the short skill summary uses mailbox-routing wording that matches the implemented skill boundary.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-agent-messaging-skill`: align the messaging skill contract with the implemented mailbox handoff boundary.
- `houmao-agent-gateway-skill`: replace stale mailbox-skill delegation targets with the current mailbox skill family.
- `docs-cli-reference`: align the system-skills reference requirements with the messaging-versus-mailbox skill split.
- `docs-readme-system-skills`: tighten the README summary wording for `houmao-agent-messaging` so it describes mailbox routing rather than mailbox ownership.

## Impact

- OpenSpec requirements for the packaged system-skill surface
- Follow-on docs and skill-asset edits that rely on those requirements
- No new runtime capability, API, or installer behavior; this is a contract-alignment change
