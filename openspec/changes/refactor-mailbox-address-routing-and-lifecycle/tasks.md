## 1. Refactor Mailbox Registration Foundations

- [ ] 1.1 Replace the current principal-scoped mailbox schema with a `mailbox_registrations` model keyed by `registration_id`, including SQLite-enforced “one active registration per address” invariants and registration-scoped `mailbox_projections` / `mailbox_state` tables.
- [ ] 1.2 Refactor canonical recipient-history storage so delivered message history stays address-snapshot-oriented and does not depend on a live mailbox-registration row continuing to exist.
- [ ] 1.3 Add one shared address-to-path-segment helper, tighten address validation for filesystem usage, and switch active mailbox directory naming from `mailboxes/<principal>` to literal `mailboxes/<address>`.
- [ ] 1.4 Keep protocol version `1`, add explicit stale-root detection for the earlier principal-keyed mailbox layout where practical, and make bootstrap failures direct operators to delete and re-bootstrap unsupported mailbox roots.
- [ ] 1.5 Add or update unit tests for registration uniqueness, address-based mailbox path naming, and stale-root rejection behavior.

## 2. Add Address-Scoped Locking And Managed Lifecycle Scripts

- [ ] 2.1 Replace principal-id lock acquisition with address-scoped locking under `locks/addresses/`, keeping `index.lock` and deterministic lexicographic acquisition order across delivery, mailbox-state mutation, register, deregister, and repair flows.
- [ ] 2.2 Implement a managed `register_mailbox.py` helper that supports `safe`, `force`, and `stash` join modes and follows the existing `--mailbox-root` plus `--payload-file` JSON contract.
- [ ] 2.3 Implement a managed `deregister_mailbox.py` helper that supports `deactivate` and `purge` cleanup modes and follows the existing `--mailbox-root` plus `--payload-file` JSON contract.
- [ ] 2.4 Materialize the new lifecycle helpers in the managed `rules/scripts/` asset set, keep `requirements.txt` aligned, and add tests that verify bootstrap publishes the expanded helper set plus the new script contract expectations.

## 3. Refactor Delivery, State, And Repair Around Registrations

- [ ] 3.1 Update managed delivery to resolve sender and recipient addresses through active mailbox registrations and attach projections or mutable mailbox state to concrete `registration_id` values rather than only to owner principals.
- [ ] 3.2 Update `purge`, `deactivate`, and `stash` behavior so registration-scoped mutable state is cleaned up appropriately while canonical message history remains intact.
- [ ] 3.3 Update repair or reindex logic so recovered mailbox registrations, historical stashed artifacts, inactive registrations, and address-scoped locks remain consistent with the refactored registration model.
- [ ] 3.4 Add unit and integration coverage for address-routed delivery, safe or force or stash registration flows, deactivate or purge cleanup, and symlink-backed mailbox deregistration behavior.

## 4. Tighten Runtime Mail Command Contracts And Bindings

- [ ] 4.1 Remove `--instruction` from runtime `mail send` and `mail reply`, add `--body-content`, and enforce full mailbox-address validation for `--to` and `--cc` in the runtime CLI.
- [ ] 4.2 Update runtime mailbox prompt construction so `send` and `reply` payloads carry explicit address lists and explicit body content without any `instruction` field.
- [ ] 4.3 Refactor runtime mailbox env binding resolution so `AGENTSYS_MAILBOX_FS_INBOX_DIR` follows the active mailbox registration path rather than `principal_id` string concatenation.
- [ ] 4.4 Update runtime mail command tests and end-to-end mailbox runtime contract coverage, including `tests/unit/agents/brain_launch_runtime/test_mail_commands.py`, `tests/integration/agents/brain_launch_runtime/test_mailbox_runtime_contract.py`, and any mailbox-binding tests affected by the address-based inbox path.

## 5. Align Docs And Validate The Refactor

- [ ] 5.1 Update mailbox skill references, filesystem layout docs, mailbox Q&A examples, and operator-facing docs so they teach address-first routing, address-based mailbox and lock paths, explicit body inputs, and managed join or leave lifecycle scripts.
- [ ] 5.2 Run the relevant formatting, lint, type-check, unit, and runtime-focused test commands for the mailbox and brain-launch-runtime modules, then capture any follow-up artifact adjustments needed before implementation is considered complete.
