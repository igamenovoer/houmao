## 1. Finalize Remaining Runtime Decisions

- [x] 1.1 Resolve the remaining blocking design questions from `review/review-20260311-102408.md` about mailbox skill injection and mailbox enablement, then update the affected proposal/design/spec artifacts to match those decisions.
- [x] 1.2 Resolve the remaining runtime contract questions from `review/review-20260311-102408.md` about structured `mail` response parsing, manifest persistence, and malformed-response error handling, then align the runtime and system-skill specs.
- [x] 1.3 Fold the remaining review-driven spec polish into the change artifacts, including symlink/platform expectations, lock-ordering semantics, SQLite non-WAL constraints, staging cleanup semantics, and future true-email non-goals.

## 2. Build Canonical Mailbox Foundations

- [x] 2.1 Add canonical mailbox protocol models and validation helpers for principals, message envelopes, attachment metadata, and `message_id` generation using the `msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}` format.
- [x] 2.2 Add filesystem mailbox bootstrap logic that creates or validates `protocol-version.txt`, the mailbox directory tree, the SQLite schema, staging, and initial in-root principal registration without depending on pre-existing `rules/scripts/`.
- [x] 2.3 Add tests for canonical message serialization, UUID-based message id generation, protocol-version handling, and bootstrap-created placeholder `archive/` and `drafts/` directories.

## 3. Materialize Managed Filesystem Mailbox Operations

- [x] 3.1 Package and materialize the managed `rules/` assets, including `deliver_message.py`, `insert_standard_headers.py`, `update_mailbox_state.py`, `repair_index.py`, and any supporting `README` or protocol notes required at mailbox initialization time.
- [x] 3.2 Implement delivery and mailbox-state mutation behavior behind the managed helper scripts, including lexicographic principal lock ordering, `index.lock` coordination, symlink projection writes, and explicit failures for missing or invalid principal registrations.
- [x] 3.3 Implement recovery and cleanup behavior behind the managed helper scripts, including reindex or repair flows, deterministic mailbox-state defaults, and staged-message cleanup after interrupted writes.
- [x] 3.4 Materialize the managed `rules/scripts/requirements.txt` dependency manifest for mailbox-local Python helpers and add tests that verify bootstrap publishes it alongside the managed script set.

## 4. Integrate Mailbox Support Into Runtime Session Startup

- [x] 4.1 Extend the build/start pipeline with the finalized mailbox enablement configuration and propagate that configuration through launch planning, brain manifests, and any required persisted session-manifest state.
- [x] 4.2 Add runtime-owned mailbox skill projection or injection using the finalized design so mailbox-enabled sessions receive the filesystem mailbox skill set in the correct tool-adapter destination and namespace.
- [x] 4.3 Populate and refresh the `AGENTSYS_MAILBOX_*` environment contract for active sessions, including filesystem-specific bindings and backend-specific runtime update behavior.

## 5. Add Agent-Mediated Mail Runtime Commands

- [x] 5.1 Add the `mail check`, `mail send`, and `mail reply` CLI flows for resumed sessions using the same session-resolution path as existing runtime control commands.
- [x] 5.2 Implement runtime-owned mailbox prompt construction, structured metadata injection, and sentinel-delimited mailbox-result parsing or validation according to the finalized runtime contract.
- [x] 5.3 Add explicit runtime errors for busy sessions, malformed mailbox responses, missing mailbox bootstrap assets, and other failure cases required by the finalized `mail` command design.

## 6. Verify End-to-End Behavior And Documentation

- [x] 6.1 Add integration coverage for mailbox bootstrap, managed-script and dependency-manifest materialization, mailbox delivery and reply flows, mailbox binding refresh, and session resume behavior.
- [x] 6.2 Align change-local mailbox skill and reference artifacts with the implemented runtime behavior, including managed-script ownership, dependency-manifest publication, placeholder directory semantics, and filesystem layout guarantees.
- [x] 6.3 Run the relevant formatting, lint, type-check, unit, and runtime-focused test commands for the mailbox implementation, then capture any follow-up doc or artifact adjustments needed before apply or archive.
