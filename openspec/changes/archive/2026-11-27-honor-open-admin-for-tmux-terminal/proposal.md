# Proposal

## Why

A verified empty gateway admin roster grants reachable callers the `agent-admin` role. The browser tmux terminal currently requires an enrolled admin key even in that mode, which blocks interactive access on an open gateway.

## What Changes

- Accept the gateway's open admin authority for interactive tmux on the existing direct owner-local routes. Keyed gateways require proof from a current enrolled administrator. An unavailable policy denies interactive access.
- Offer **Interact with tmux** on eligible open and keyed gateway dashboards. Open gateways issue an interactive ticket without sign-in. Keyed gateways use the existing administrator sign-in flow.
- Let `gateway terminal-entry --interact` request an unsigned link on a verified open gateway. Bind the link and resulting attachment to the exact open epoch or enrolled key that authorized it.
- Keep read-only viewing anonymous and apply the existing owner-local transport and live tmux checks to both entry modes.

## Capabilities

### New Capabilities

### Modified Capabilities

- `authenticated-gateway-access` applies the gateway's open admin authority to interactive tmux and defines how roster changes invalidate tickets and streams.
- `gateway-dashboard` exposes the interactive action and entry guidance for open and keyed rosters.
- `houmao-srv-ctrl-native-cli` adds unsigned interactive ticket issuance for the verified open roster.

## Impact

The change affects gateway authorization, interactive ticket issuance and redemption, the dashboard, the bundled browser entry page, and the scoped CLI. Operator and protocol references will describe the open-roster behavior and roster transitions.
