# Design

## Context

Gateway route admission already supplies `basis="open"` with an `open_epoch` for a verified empty roster. The terminal ticket route and stream currently require `basis="admin"` through the same per-key check used by terminal SSHSIG login. Separately, the dashboard, browser page, CLI, and gateway client assume that every interactive request needs a signing key.

## Goals / Non-Goals

Use the existing gateway admin decision to enter the interactive tmux terminal on a verified open roster. Keep the decision bound to the original caller and roster state until disconnect. This change covers the existing owner-local gateway surfaces and uses the current ticket format, tmux lifecycle, and anonymous read path.

## Decisions

### Reuse the Original Authorization Decision

Keep `POST /v1/admin/terminal/attach/ticket` classified as `admin.terminal.interact`. Use the admission middleware's original `GatewayGrant`. Give the terminal ticket path a shared check that accepts that exact effect with `basis="open"` or `basis="admin"` and uses the existing policy revalidation. On open grants, revalidation checks the same verified empty roster and `open_epoch`. On keyed grants, it checks the same key and enrollment revision. The SSHSIG browser login still uses the enrolled-key check for candidate selection and approval. First-key enrollment keeps its existing proof requirement.

Apply the shared check before and after target resolution for issuance, when a ticket is redeemed, and in the active stream's current checks. The interactive ticket always carries the admitting grant, including for an anonymous open caller. Keep its existing listener, generation, exact tmux binding, mode, and expiry checks. If the first admin enrolls or the original admin loses qualification, the old ticket or stream loses authority. A later empty roster creates a fresh epoch, so prior grants cannot resume under it.

### Offer Direct Browser Entry on an Open Gateway

Render the same bare interactive link for an eligible owner-local gateway in either verified roster mode. Keep the dashboard read-only. The interactive page without a fragment can request the existing ticket endpoint on the same origin. An open gateway returns a ticket for the interactive stream. When the request requires proof, the page offers the existing admin SSHSIG sign-in action. This uses the live policy at ticket issuance even when the dashboard rendered earlier. An unavailable policy shows an error. A link with a fragment still redeems its existing ticket directly, and browser code verifies the ticket's mode, origin, and path before connecting.

### Select the CLI Proof Mode From the Current Verified Gateway

Keep read-only link requests unsigned. For `--interact`, a verified open gateway uses an unsigned direct client when the caller supplies no explicit `--signer`. A keyed gateway uses the explicit signer or configured administrator signer. An explicit signer on an open gateway follows the existing native Web entry convention and is checked as submitted. A failed attempt returns its refusal. Allow unsigned interactive requests in `GatewayClient` under the same owner-local and proxy exclusions, and keep proof bindings limited to direct caller credentials where a signer is supplied.

Reuse the CLI's unsigned post-issuance identity comparison for open interactive tickets. The CLI checks the same target, generation, and listener before printing the result. The gateway always performs current roster admission and validates the original grant again before attaching.

## Risks / Trade-offs

- Roster state can change between dashboard render, browser ticket request, and WebSocket redemption. Use live policy admission and original-grant revalidation at each boundary. Return fresh-entry guidance when the selected authority expires.
- Interactive access now follows open gateway policy for callers that can reach its owner-local address. Keep the existing exact origin, direct transport, and session checks. Document both roster modes and the effect of enrolling the first administrator.

## Migration Plan

Install the updated gateway and CLI together and restart the gateway through the existing lifecycle command. The persisted roster and revisions keep their current format. Restarting clears outstanding in-memory tickets. Rollback uses the prior package and the same lifecycle command.
