## Context

The live gateway already has the right core ingredients for mailbox wake-up behavior: it discovers mailbox capability from the runtime-owned session manifest, polls unread state from mailbox-local SQLite, and enqueues an internal `mail_notifier_prompt` only when gateway-owned admission and execution conditions say the session is idle enough to receive it. What is missing is a dedicated, reproducible operator surface that proves those behaviors in a real CAO-backed session and makes them easy to inspect after the fact.

The existing mailbox roundtrip tutorial pack is intentionally not that place. The in-progress mailbox-roundtrip stabilization work keeps gateway notifier behavior as optional follow-up context so the roundtrip tutorial can stay focused on direct runtime `mail send -> mail check -> mail reply -> mail check`. Folding gateway attach, notifier enablement, manual mailbox injection, and busy-session auditing into that pack would blur the line between mailbox truth and gateway-owned wake-up behavior.

The current notifier observability contract is also slightly weaker than the requested demo matrix. The gateway keeps a human-readable `gateway.log`, but repetitive empty, dedup, and busy messages are rate-limited. That is good for tailing a live log, but it is not enough when a demo or test matrix wants to review each poll decision with explicit timing, busy-state inputs, and enqueue-versus-skip outcomes.

## Goals / Non-Goals

**Goals:**

- Add a dedicated tutorial pack under `scripts/demo/` for gateway-driven mailbox wake-up behavior.
- Support both automatic and manual demo flows from one pack.
- Keep the notifier contract explicitly unread-set based rather than per-message based.
- Let operators inject one email from inline content or a body file and inject multiple emails in quick succession without touching SQLite directly.
- Verify wake-up behavior through stable gateway-owned artifacts such as notifier status, audit history, queue state, mailbox unread state, and a demo-owned output file.
- Extend gateway notifier auditing so each enabled poll cycle leaves structured decision data in a queryable SQLite audit surface suitable for later review and report generation.

**Non-Goals:**

- Making the mailbox roundtrip tutorial pack depend on gateway attachment or notifier enablement.
- Changing public gateway request kinds beyond the existing externally submitted surface.
- Requiring one wake-up prompt per unread message.
- Making model-specific transcript text the main golden verification contract.
- Replacing the mailbox managed-script mutation boundary with direct ad hoc filesystem or SQLite writes.

## Decisions

### Decision 1: Add a separate `gateway-mail-wakeup-demo-pack` instead of extending the mailbox roundtrip tutorial

The new demo will live in its own directory under `scripts/demo/`. Its job is to demonstrate gateway-specific behavior: attach, notifier enablement, unread-set detection, busy deferral, manual delivery, automatic delivery, and wake-up verification.

This keeps the mailbox roundtrip tutorial aligned with its current scope while giving the gateway notifier a tutorial surface that can be richer, more stateful, and more inspection-heavy.

Alternatives considered:

- Extend `mailbox-roundtrip-tutorial-pack` with gateway attach and notifier steps. Rejected because that pack is intentionally staying gateway-optional and mailbox-first.
- Document notifier behavior only in reference docs. Rejected because the missing piece is a runnable, tracked verification surface rather than prose alone.

### Decision 2: Use one mailbox-enabled managed agent plus an external injector

The demo will use one live mailbox-enabled CAO-backed agent session and one demo-owned external mail injector. The injector is not a second managed agent session. It exists only to deliver mail into the shared mailbox root through the supported managed delivery boundary.

This isolates the gateway wake-up problem from the general two-agent mailbox roundtrip problem. It also matches the requested manual cases more naturally, because “manual send” means operator-authored mail arrival rather than one more runtime-controlled agent workflow.

Alternatives considered:

- Use two full managed agents and runtime `mail send` as the only delivery path. Rejected because it duplicates the mailbox roundtrip story and makes it harder to tell whether the demo is proving mailbox delivery or notifier wake-up.
- Deliver mail by writing SQLite rows or projection files directly. Rejected because the mailbox contract already defines `deliver_message.py` as the mutation boundary for this class of operation.

### Decision 3: The pack will combine a one-shot automatic path with a stateful manual workflow

The runner surface will support both:

- one-shot automatic execution for the maintainer-style proof, and
- stateful manual commands for interactive operator inspection.

The exact wrapper names can still be implementation-shaped, but the workflow will cover the equivalent of:

- `run` or `auto`
- `start`
- `manual-send`
- `manual-send-many`
- `inspect`
- `verify`
- `stop`

This follows the tutorial-pack structure from the mailbox roundtrip pack while borrowing the long-lived, inspectable feel of the interactive CAO demo.

Alternatives considered:

- Only a single opaque `run_demo.sh` one-shot flow. Rejected because the requested manual cases need persistent state and repeatable injection into a live session.
- Only subcommands with no end-to-end one-shot path. Rejected because maintainers still need a simple reproducible command that refreshes or compares one expected report.

### Decision 4: Mail injection stays behind the mailbox managed-script boundary, but the demo wrapper will be operator-friendly

The pack will not ask operators to hand-author full managed delivery payload JSON unless they choose to inspect it. Instead, the wrapper or helper layer will accept operator-friendly inputs such as `--body-content` and `--body-file`, then materialize the staged Markdown and `DeliveryRequest` payload needed by `rules/scripts/deliver_message.py`.

This preserves the mailbox contract while keeping the demo ergonomic.

Alternatives considered:

- Require raw payload-file authoring in the main happy path. Rejected because the tutorial would become more about mailbox script plumbing than gateway wake-up behavior.
- Introduce a new runtime CLI command just for this demo. Rejected because the change is tutorial- and gateway-focused rather than a broad runtime-CLI expansion.

### Decision 5: The notifier contract for this demo is unread-set based, not per-message based

When the notifier poll sees unread mail, it is answering one question: “does unread mail exist right now, and is the session eligible for a wake-up prompt?” It is not promising one prompt per message.

If multiple unread messages are present in one poll cycle, the gateway may send one reminder prompt that summarizes the unread set, including message titles and identifiers. If that unread set stays unchanged, later polls may deduplicate rather than enqueueing duplicate reminders. If the unread set changes, a later poll may enqueue a fresh reminder when the session is eligible.

That means burst tests will assert “no unread mail missed” rather than “one wake-up per email.”

Alternatives considered:

- Define notifier behavior as one wake-up per delivery event. Rejected because it creates needless prompt spam and does not match the current unread-set digest model.

### Decision 6: Required verification will focus on gateway-owned evidence first, with transcript evidence only as supplemental

The golden report will treat these as required proof points:

- notifier enablement and runtime status,
- structured notifier-decision audit history,
- queue and event artifacts that show notifier enqueue and execution,
- mailbox-local unread state,
- the demo-owned output file written by the agent in the automatic case.

Transcript or terminal-tail evidence can still be collected for debugging and human inspection, but it will remain supplemental rather than the primary golden contract because tool-specific output can drift.

The sanitized golden snapshot will reduce notifier audit evidence to stable outcome-summary facts rather than exact per-poll sequences. Raw or debug artifacts may still retain full per-poll audit rows for investigation, but `expected_report/report.json` should only assert reproducible facts such as notifier enablement, observed outcome types, absence of poll errors, and output-file evidence.

Alternatives considered:

- Make the expected report assert exact agent transcript text. Rejected because the gateway mechanism can be correct even if model phrasing drifts.

### Decision 7: Add complete structured notifier-decision auditing while keeping `gateway.log` human-friendly

The gateway will continue to keep `gateway.log` as a tail-friendly human log, and it may continue to rate-limit repetitive human-facing lines. Separately, it will record one structured notifier decision row for each enabled poll cycle in a dedicated `gateway_notifier_audit` table inside `queue.sqlite`.

Each structured record will include enough information to explain what happened, including at minimum:

- poll time,
- unread count,
- the unread-set identity or summary used for deduplication,
- gateway admission state,
- active execution state,
- queue depth,
- decision outcome such as `empty`, `dedup_skip`, `busy_skip`, `enqueued`, or `poll_error`,
- request id when a notifier prompt is enqueued,
- explicit skip or error detail when relevant.

For v1, that SQLite audit table is the authoritative durable history surface for detailed notifier decisions. `events.jsonl` stays focused on request lifecycle entries, and `GET /v1/mail-notifier` remains a compact status snapshot rather than the source of full per-poll decision detail. Demo inspect and verify commands will read the audit table directly from the gateway root.

Alternatives considered:

- Emit every poll only to `gateway.log`. Rejected because the current rate-limited human log is not a reliable per-cycle audit surface.
- Mirror every poll into `events.jsonl`. Rejected because one-second poll cadence would flood the request event stream and make demo verification less queryable.
- Add per-poll detail only to `GET /v1/mail-notifier`. Rejected because a status endpoint is a snapshot, not durable history.

### Decision 8: The automatic idle-mail injector uses CAO terminal status for mail timing, but busy-deferral assertions stay gateway-native

For the automatic case, a demo-owned helper will check the live CAO terminal state every three seconds and deliver a mail only when the agent appears idle. That keeps the automatic scenario simple and avoids injecting a wake-up task while the agent is obviously still busy from prior work.

For the busy-deferral scenario, however, the demo will create “busy” through gateway-managed work rather than relying solely on CAO status. The gateway’s own deferral logic is based on admission, active execution, and queue depth, so the demo should exercise that path directly when it wants to prove busy skipping.

Alternatives considered:

- Use CAO terminal status as the sole truth for gateway busy semantics. Rejected because the gateway’s actual eligibility decision is gateway-owned rather than a direct mirror of CAO terminal status.

### Decision 9: Default to launcher-managed loopback CAO, demo-owned output roots, and pack-local helpers for v1

The new pack will follow the repository’s newer demo direction and default to launcher-managed loopback CAO plus a demo-owned output root that holds workspace, runtime, mailbox, gateway, and report artifacts. For v1, the pack keeps its helper logic under its own tutorial-pack directory so it remains self-contained. If nearby tutorial-pack changes land first with a stable helper surface, this pack may reuse narrow pieces opportunistically, but it should not depend on a new shared-helper extraction to stay coherent.

Alternatives considered:

- Depend on an ambient externally managed CAO instance by default. Rejected because that has already proven too fragile for reproducible tutorial-pack behavior.
- Extract a shared demo-helper module as part of this change. Rejected because the nearby mailbox-roundtrip stabilization work is still moving and this change should not grow into a cross-pack refactor.

## Risks / Trade-offs

- [Risk] The new pack could duplicate launcher-management and workspace-helper logic already being added to the mailbox tutorial path. → Mitigation: keep helpers pack-local in v1, align directory layout and naming with the nearby tutorial work, and only reuse stable helper pieces opportunistically.
- [Risk] The automatic “write the current time to a file” scenario still depends on model/tool behavior. → Mitigation: keep the golden assertion narrow: the file exists at the expected path, is newer than delivery, and contains a parseable timestamp rather than exact transcript text.
- [Risk] Burst deliveries can land within one poll window and produce fewer reminder prompts than delivered messages. → Mitigation: treat this as correct unread-set behavior and verify absence of missed unread mail rather than prompt count equality.
- [Risk] Exact poll timing varies across environments and could make a report fragile if it asserts raw notifier sequence. → Mitigation: keep the golden report summary-shaped and preserve full audit rows only in raw or debug artifacts.
- [Risk] Manual and automatic flows could make the pack feel too large. → Mitigation: keep the one-shot path as the maintainer default and treat the manual commands as explicit operator tools rather than the only workflow.

## Migration Plan

No user-data migration is required. This change adds a new demo pack and extends gateway-owned notifier auditing. Older gateway roots simply lack the new `gateway_notifier_audit` table until the updated schema is created by the new code and the notifier is exercised. Rollback is limited to removing the new demo pack and reverting the notifier auditing extension.

## Open Questions

None at this time. Review decisions for audit storage, helper ownership, notifier status surface, and golden-report sanitization have been folded into this design.
