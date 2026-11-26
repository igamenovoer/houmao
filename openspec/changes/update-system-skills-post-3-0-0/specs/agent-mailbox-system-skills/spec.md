# Spec Delta

## ADDED Requirements

### Requirement: Gateway email-processing skill covers compact reply receipts and permission failure handling
`houmao-process-emails-via-gateway` SHALL document compact `POST /v1/mail/{channel}/reply` write receipts (`message_ref` + `peek` reconciliation on the same binding) and explicit fail-closed reporting on `mail.reply` or `mail.attachment.owner_file` authorization failures.

#### Scenario: Agent reconciles reply receipts and permission refusals during a round
- **WHEN** a managed agent replies to or attaches files for a notified email during a gateway round
- **THEN** the workflow uses the returned top-level `message_ref` (and optional `peek`) to verify reply delivery instead of expecting full legacy body echoes
- **AND THEN** any `mail.reply` or `mail.attachment.owner_file` denial aborts that message's archive step and leaves it open for follow-up

### Requirement: Gateway email-processing skill adopts progressive disclosure into commands and references
`houmao-process-emails-via-gateway` SHALL refactor its 169-line `SKILL-MAIN.md` monolith into a lean ~70-line router (`SKILL-MAIN.md`) with `commands/process-round.md` (carrying its own numbered `## Workflow` and fallback) and `references/reply-hardening.md` (carrying the reminder contract and prompt template) per `imsight-agent-skill-handling`.

#### Scenario: Entrypoint stays concise while round procedure and template live in subfiles
- **WHEN** a reviewer inspects `houmao-process-emails-via-gateway`
- **THEN** `SKILL-MAIN.md` provides concise `## Workflow`, `## Actor Frame Gate`, `## Subcommands` (`help`, `process-round`), and `## Guardrails`
- **AND THEN** `commands/process-round.md` owns the bounded round steps and `references/reply-hardening.md` owns the reminder payload and template

### Requirement: Gateway email-processing skill preserves fail-closed round, reply-hardening, and non-polling invariants
`houmao-process-emails-via-gateway` SHALL preserve agent-only `## Actor Frame Gate`, fail-closed reliance on prompt-supplied `gateway_base_url`, `channel`, and `expected_binding_id`, stalled-work-first ordering, `one_off` lowest-priority (`--after-all` / `start_after_seconds: 15`) reply hardening, reply-before-archive, and stopping without polling.

#### Scenario: Missing gateway URL or binding mismatch terminates the round fail-closed
- **WHEN** a notifier prompt lacks `gateway_base_url`, `channel`, or `expected_binding_id`, or the binding mismatches
- **THEN** `houmao-process-emails-via-gateway` stops with a contract failure without running `resolve-live`
- **AND THEN** processed rounds archive only succeeded messages after reply and stop without polling for new mail
