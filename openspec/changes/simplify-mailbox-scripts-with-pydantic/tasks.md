## 1. Refactor Managed Mailbox Payload Boundaries

- [ ] 1.1 Introduce strict pydantic request models for managed mailbox delivery, mailbox-state mutation, repair, registration, and deregistration payloads, reusing shared mailbox validators where appropriate.
- [ ] 1.2 Replace the current hand-written `from_payload()` constructors and manual helper validators in `src/gig_agents/mailbox/managed.py` with schema-backed parsing and explicit validation error conversion.
- [ ] 1.3 Centralize the common wrapper-script execution path so the projected Python helpers share one parse, validate, error, and JSON-emission flow while preserving the existing CLI flags.

## 2. Align Projected Mailbox Assets And Dependency Contracts

- [ ] 2.1 Keep `src/gig_agents/mailbox/assets/rules/scripts/requirements.txt` aligned with the actual managed helper imports and declare `pydantic` as an intentional required dependency for the Python helper set using a minimum-version-only specifier.
- [ ] 2.2 Update the projected Python helper scripts under `src/gig_agents/mailbox/assets/rules/scripts/` to use the simplified shared validation or runner pattern without changing their filenames or invocation contract.
- [ ] 2.3 Update mailbox protocol notes or related docs so the managed helper dependency manifest and strict structured validation contract are documented consistently with the projected rules asset set.

## 3. Verify Validation Behavior And Regression Coverage

- [ ] 3.1 Add unit coverage for valid and invalid managed mailbox payloads across delivery, state-update, repair, registration, and deregistration entrypoints.
- [ ] 3.2 Add regression tests that verify validation failures return one structured JSON error result and do not partially mutate mailbox files or SQLite state.
- [ ] 3.3 Run the relevant formatting, lint, type-check, unit, and runtime mailbox test commands and capture any follow-up adjustments needed before implementation is considered complete.
