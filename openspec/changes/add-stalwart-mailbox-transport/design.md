## Context

Houmao’s current mailbox behavior was designed around a daemon-free filesystem transport. That transport needs Houmao to emulate mailbox invariants itself through managed scripts, lock files, mailbox-root policy files, projection symlinks, and SQLite state. Those mechanisms are valid for the filesystem transport, but they are implementation details of that transport rather than universal mailbox semantics.

The repository now includes a local Stalwart bring-up path, which makes it practical to host real mailboxes for local and integration environments. Stalwart already provides mailbox delivery, mailbox folders, read or unread state, reply threading surfaces, and mailbox account management. This change uses that real mail system as the transport authority instead of porting the filesystem transport’s repair and integrity machinery into a second backend.

This change also needs to coexist with the current runtime UX:

- mailbox support is bound to a started or resumed session,
- the operator uses `mail check`, `mail send`, and `mail reply`,
- mailbox behavior stays runtime-owned instead of role-authored,
- existing filesystem transport flows remain available unless later deprecated explicitly.

## Goals / Non-Goals

**Goals:**

- Add a Stalwart-backed mailbox transport that Houmao can configure and use for live mailbox-enabled sessions.
- Treat Stalwart as the source of truth for mailbox delivery, mailbox folder state, and transport-level integrity.
- Keep a small transport-neutral mailbox contract in Houmao: participant identity, async mailbox participation, explicit reply ancestry, operator `mail` UX, and structured mailbox results.
- Keep mailbox transport behavior runtime-owned through projected mailbox system materials and runtime-managed bindings.
- Use a mailbox-resident welcome thread to publish shared agent mailbox conventions that do not need to live in filesystem `rules/`.
- Preserve the existing filesystem transport as a separate transport with its current transport-specific rules.

**Non-Goals:**

- Re-implementing Stalwart semantics in local SQLite, lock files, or a Houmao-managed canonical message corpus.
- In-place migration of an existing live filesystem mailbox root into Stalwart-backed mailboxes.
- Making gateway notifier behavior transport-generic in the same change.
- Replacing the existing filesystem transport in this change.
- Defining long-term multi-provider email abstractions beyond the first Stalwart-backed implementation.

## Decisions

### Decision 1: Filesystem mailbox mechanics are transport-local, not mailbox-global

The mailbox contract will be split into:

- transport-neutral mailbox semantics that Houmao still owns, and
- transport-specific mechanics that each transport owns for itself.

Filesystem-specific artifacts such as `rules/`, `rules/scripts/`, projection symlinks, `index.sqlite`, mailbox-local SQLite, and address lock files remain valid for the filesystem transport, but they are no longer treated as the normative mailbox protocol for every transport.

Why:

- A real mail system already enforces delivery integrity and mailbox consistency.
- Carrying the filesystem transport’s repair machinery into Stalwart would preserve complexity without preserving value.

Alternatives considered:

- Port the filesystem transport contract verbatim into Stalwart. Rejected because it would duplicate server-owned behavior and force Houmao to maintain a second integrity layer on top of a real mail server.

### Decision 2: Stalwart uses management API for provisioning and JMAP as the primary automation surface

The Stalwart-backed transport will use:

- Stalwart management API for domain and account provisioning,
- JMAP as the primary mailbox automation surface for `check`, `send`, `reply`, and mailbox-state reads or updates,
- SMTP and IMAP as compatibility or debugging surfaces rather than the primary automation contract.

Why:

- Provisioning and mailbox operations are separate concerns and should use the server surface designed for each.
- JMAP is better aligned with structured mailbox operations than scraping IMAP state or mixing SMTP send with IMAP reads.
- IMAP and SMTP remain useful for manual inspection and interoperability testing.

Alternatives considered:

- IMAP plus SMTP as the primary programmatic interface. Rejected because it is more stateful, less structured, and more cumbersome for precise mailbox automation.
- SMTP submission only with no mailbox read API. Rejected because Houmao needs mailbox read or unread and reply workflows, not just outbound delivery.

### Decision 3: Keep the current session-facing `mail` UX and mailbox result contract

Houmao will keep the existing operator-facing `mail check`, `mail send`, and `mail reply` command surface plus structured mailbox results. The runtime continues to resolve mailbox support from the session binding and to persist that binding in the manifest.

For the first Stalwart-backed implementation, mailbox transport actions remain session-mediated through runtime-owned mailbox prompt contracts and projected mailbox system materials, but those materials become transport-specific. Filesystem sessions continue to consult `rules/` and managed scripts; Stalwart sessions instead use real-mail guidance and Stalwart-backed transport bindings.

Why:

- This preserves the current runtime control model and avoids introducing a second mailbox command surface in the same change.
- Agents can inspect the same mailbox content and welcome thread that humans or external tools can inspect.
- The runtime keeps one consistent structured result boundary for mailbox operations across transports.

Alternatives considered:

- Move Stalwart mailbox operations entirely into runtime-owned direct client code with no session-mediated transport actions. Deferred because it is a larger architectural change and would create two very different mailbox execution models in one step.

### Decision 4: Shared mailbox conventions move into a mailbox-resident welcome thread

For Stalwart-backed mailboxes, shared agent mailbox conventions that do not need hard runtime enforcement will be delivered as a welcome message or welcome thread inside the mailbox system itself. That message can include:

- transport usage conventions,
- expected structured reply formats,
- thread and subject conventions,
- pointers to mailbox docs or attached protocol examples.

The runtime binding remains the infrastructure source of truth for how to reach the mailbox, while the welcome thread becomes the agent-facing operating manual inside the mailbox.

Why:

- It uses the real mailbox as the place where mailbox participants actually look.
- It avoids recreating a filesystem-only `rules/` tree for a real mail transport.

Alternatives considered:

- Keep Stalwart transport instructions in projected skill text only. Rejected because some shared conventions are better represented as mailbox content visible to all participants.
- Treat the welcome thread as the only source of mailbox configuration. Rejected because runtime startup and resume still need a local binding independent of mutable mailbox content.

### Decision 5: Stalwart credentials stay out of the persisted manifest payload

The persisted session manifest remains secret-free. Stalwart transport bindings in the manifest identify the mailbox transport, participant identity, mailbox address, endpoints, and transport-safe metadata, but they do not persist mailbox secrets inline.

Runtime-managed secret material for Stalwart-backed sessions will need a transport-specific handling path such as session-owned secret files, credential references, or runtime-side secret lookup, while keeping the manifest and shared registry secret-free.

Why:

- The current mailbox manifest contract is intentionally secret-free.
- Real mail transport requires stronger credential handling than a local filesystem path.

Alternatives considered:

- Persist mailbox passwords or tokens in the launch-plan payload. Rejected because it would violate the existing secret-free manifest boundary.

## Risks / Trade-offs

- [Risk] Agent-mediated Stalwart access introduces mailbox credentials into the launched session boundary. → Mitigation: use transport-scoped credentials, keep them out of the manifest, and prefer runtime-managed secret references over plain persisted values.
- [Risk] The current mailbox protocol carries filesystem-shaped assumptions such as generated `message_id` formats and path-based attachments. → Mitigation: narrow the transport-neutral protocol to semantics Houmao truly owns and move transport-owned identifiers into transport-specific bindings or metadata.
- [Risk] Two mailbox transports can diverge in user-visible behavior. → Mitigation: keep the shared CLI UX and structured result contract stable, and write explicit spec deltas that separate transport-neutral semantics from transport-specific behavior.
- [Risk] Gateway notifier remains filesystem-oriented after this change. → Mitigation: declare transport-generic notifier support out of scope here and keep the Stalwart transport focused on session start, mailbox binding, and direct mailbox operations first.
- [Risk] Welcome-thread guidance can be deleted, moved, or ignored by participants. → Mitigation: treat the welcome thread as agent-facing guidance, not as the runtime’s infrastructure source of truth.

## Migration Plan

1. Add a new Stalwart-backed transport alongside the existing filesystem transport rather than replacing filesystem mailbox support in place.
2. Generalize mailbox runtime config and projected mailbox system materials to accept transport-specific bindings.
3. Implement Stalwart provisioning and mailbox operation flows against a local Stalwart environment.
4. Update mailbox docs to distinguish transport-neutral mailbox semantics from filesystem-only mechanics and Stalwart-backed behavior.
5. Keep existing filesystem mailbox sessions unchanged.

Rollback strategy:

- Disable or stop selecting the Stalwart transport for new sessions.
- Continue using the existing filesystem transport, whose artifacts and tests remain separate.
- No live filesystem mailbox root needs conversion back from Stalwart because this change does not require in-place migration.

## Open Questions

- Should the first Stalwart-backed implementation use direct account passwords, app passwords, or another credential form for session mailbox access?
- Should the runtime pre-seed the welcome thread only for newly provisioned mailboxes, or re-send or repair it when missing?
- Which Stalwart mailbox identifiers should Houmao persist for reply targeting: server-native message ids, RFC-style `Message-ID` headers, or both?
- How much mailbox content should `mail check` return in structured form before asking the agent to interpret it?
