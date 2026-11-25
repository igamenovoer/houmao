# Tasks

## 1. Retained Authorization and Status-Only Access

- [ ] 1.1 Remove the selectable observer tier from the authorization catalog. Add retained principal fallback settings and their handoff authority. Verify the lowest requester effects, exact status-only access, independent anonymous admission, remaining role precedence, and queued fallback invalidation in gateway authorization tests.
- [ ] 1.2 Migrate retained observer defaults and assignments before serving their policies. Verify status-only defaults, active and expired observer assignments, overlapping direct grants, unchanged credentials, and policy restart against databases in the previous format. Verify that migration never grants requester effects.
- [ ] 1.3 Expose the effective-admin fallback setter through the gateway, verified passive endpoint, and explicit owner-local CLI path. Add inspection and help output for the retained default and each principal’s fallback. Test unauthorized callers, wrong targets, stale authority, and permission updates while the target is stopped or detached.
- [ ] 1.4 Update the gateway policy reference, manager command reference, and access skill. Verify the documented status-only sequence grants `agent.status.read`, excludes fallback, and explains the independently configured anonymous path.

## 2. Mail Transport and Keyed Online Access

- [ ] 2.1 Retire `agent.mail.deliver` from ordinary delivery. Retain active registrations, sender authentication and staged-envelope checks, binding scope, and publication integrity. Verify forged envelope and stale sender rejection, multiple recipients, and delivery to a stopped or detached managed agent.
- [ ] 2.2 Remove the online roster-mode gate from key enrollment, binding controls, direct and gateway mailbox paths, status, and notifier use. Verify both setup orders, restart, refresh/reconnect, and retained account, origin, and caller checks with normal mailbox credentials against Stalwart.
- [ ] 2.3 Preserve exact send, reply, and attachment permissions. Verify that offline and online receipts report the transport’s actual result without recipient rules or filing details. Cover confirmed receipt, refusal, and uncertainty without changing channel or sender identity. Update the messaging skill and transport guides.

## 3. Independent Owner Authorization and Backend Placement

- [ ] 3.1 Add independent owner authority enrollment and revocation for protected mail rules. Bind signed requests and backend receipts to the exact backend, mailbox, operation, revision, and request identity. Verify unsigned, forged, stale, cross-binding, and cross-operation rejection. Test exact retries and independently authenticated owner inspection and submission.
- [ ] 3.2 Add the gateway policy-apply relay and report confirmed, refused, unsupported, and uncertain results using backend evidence. Verify that ordinary mailbox credentials and gateway administrator grants cannot manufacture backend authority. Test both open and keyed admission and stale binding rejection. Document the signed mail-only payload and owner verification path.
- [ ] 3.3 Add backend-owned rules and direct Archive delivery to the trusted filesystem publisher. Verify sender registration matching, per-recipient Inbox or Archive placement with one canonical message, repair, restart, and publish-versus-update races. Test that shared writers report unsupported. Verify that runtime identities cannot obtain another mailbox’s rules or placement, or change protected placement through API or filesystem access.
- [ ] 3.4 Add the trusted management path for Stalwart-native Archive delivery. Verify provider management and placement isolation from gateway runtime credentials, direct Archive delivery while the gateway is stopped, and explicit unsupported results when native controls cannot enforce it. Document qualification independently of ordinary attachment.
- [ ] 3.5 Verify on both qualified backends that rule changes affect new deliveries and preserve existing Inbox and Archive membership. Document rule application and separately authorized Archive review.

## 4. Agent Work and Acceptance

- [ ] 4.1 Use current backend Inbox membership for work reads, both notifier modes, compaction, and queued reminders. Verify bounded observation, stale references, and notification for Inbox delivery alongside direct Archive delivery. Update prompts, runtime mailbox skills, and references to explain separately authorized filing for completed Inbox work and the existing reminder modes.
- [ ] 4.2 Verify a keyed recipient with both channels. A status-only peer can read status, cannot submit typed work, and can still send ordinary mail through its selected transport. Verify sender receipt privacy, independent owner rule authorization, and protected placement while the gateway is stopped or attempts unauthorized changes. Exercise native online filtering when qualified and verify unsupported results otherwise.
- [ ] 4.3 Run the touched gateway, offline registry, online mailbox, and notifier suites. Run `pixi run test`, `pixi run lint`, `pixi run typecheck`, `pixi run docs-build`, and strict OpenSpec validation. Record results and any deployment lanes still unverified.
