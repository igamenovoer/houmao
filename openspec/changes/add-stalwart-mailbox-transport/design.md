## Context

Houmao’s current mailbox behavior was designed around a daemon-free filesystem transport. That transport needs Houmao to emulate mailbox invariants itself through managed scripts, lock files, mailbox-root policy files, projection symlinks, and SQLite state. Those mechanisms are valid for the filesystem transport, but they are implementation details of that transport rather than universal mailbox semantics.

The repository now includes a local Stalwart bring-up path, which makes it practical to host real mailboxes for local and integration environments. Stalwart already provides mailbox delivery, unread state, reply threading surfaces, and mailbox account management. This change uses that real mail system as the transport authority instead of porting the filesystem transport’s repair and integrity machinery into a second backend.

Houmao also already has a per-agent gateway sidecar. That gateway is the right place to hide transport differences from managed agents, but the current gateway mail integration is still filesystem-specific: notifier support loads the manifest-backed mailbox binding and then reads unread truth directly from mailbox-local SQLite. That makes the gateway incapable of acting as the mailbox abstraction boundary between the filesystem transport and a real email system.

This change needs to coexist with the current runtime UX:

- mailbox support is bound to a started or resumed session,
- the operator uses `mail check`, `mail send`, and `mail reply`,
- mailbox behavior stays runtime-owned instead of role-authored,
- existing filesystem transport flows remain available unless later deprecated explicitly,
- a managed agent may use a live gateway mailbox API when available but may still fall back to direct transport-specific mailbox behavior when no gateway is attached.

For this change, the scope is intentionally narrow: only mailbox functions that both the filesystem transport and the Stalwart transport can support cleanly should become part of the shared gateway contract.

## Goals / Non-Goals

**Goals:**

- Add a Stalwart-backed mailbox transport that Houmao can configure and use for live mailbox-enabled sessions.
- Treat Stalwart as the source of truth for mailbox delivery, unread state, reply ancestry, and transport-level integrity.
- Add a gateway-owned mailbox facade for the mailbox operations both transports support cleanly: mailbox status, `check`, `send`, and `reply`.
- Keep a small transport-neutral mailbox contract in Houmao: participant identity, async mailbox participation, explicit reply targeting, operator `mail` UX, and normalized mailbox results.
- Keep mailbox transport behavior runtime-owned through projected mailbox system materials, runtime-managed bindings, and manifest-backed gateway adapter construction.
- Make gateway mail notifier behavior transport-generic by routing unread inspection through the gateway mailbox facade.
- Preserve the existing filesystem transport as a separate transport with its current transport-specific rules.

**Non-Goals:**

- Re-implementing Stalwart semantics in local SQLite, lock files, or a Houmao-managed canonical message corpus.
- In-place migration of an existing live filesystem mailbox root into Stalwart-backed mailboxes.
- Exposing transport-specific mailbox features such as folders, archive, delete, move, or star through the shared gateway API in this change.
- Replacing the existing filesystem transport in this change.
- Making mailbox provisioning, mailbox-resident welcome guidance, or server administration part of the shared gateway mailbox API.
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

### Decision 2: Gateway exposes dedicated mailbox routes separate from terminal-mutating requests

The gateway will expose dedicated mailbox routes for mailbox-enabled sessions instead of sending mailbox transport work through `POST /v1/requests`.

Shared mailbox routes for this change:

- `GET /v1/mail/status`
- `POST /v1/mail/check`
- `POST /v1/mail/send`
- `POST /v1/mail/reply`

`POST /v1/requests` remains limited to terminal-mutating work such as `submit_prompt` and `interrupt`.

Why:

- Mailbox transport I/O is not terminal mutation.
- Mailbox reads and sends should not consume the single terminal-mutation slot.
- Dedicated routes make the gateway a real transport facade rather than a prompt relay.

Alternatives considered:

- Add mailbox request kinds such as `mail_check` or `mail_send` to `POST /v1/requests`. Rejected because it would mix mailbox transport semantics with the gateway’s serialized terminal-injection queue.

### Decision 3: The shared gateway mailbox contract is limited to common operations and opaque references

The shared gateway mailbox contract in this change is intentionally small.

Supported shared operations:

- mailbox availability or status,
- `check`,
- `send`,
- `reply`.

Shared mailbox results will use normalized metadata and transport-neutral opaque references such as `message_ref` rather than exposing filesystem-local ids, SQLite row identities, or Stalwart-native JMAP object shapes directly.

Why:

- The filesystem transport and a real email system can both support these operations cleanly.
- Expanding the shared surface to folders, archive, delete, move, or star would force the first gateway abstraction to encode transport-specific semantics too early.
- Opaque references let each transport keep its own authoritative storage identity while still supporting later reply targeting.

Alternatives considered:

- Expose filesystem `message_id` or Stalwart-native ids directly in the shared contract. Rejected because it would leak transport-specific storage assumptions into managed-agent behavior.

### Decision 4: Gateway mailbox adapter construction remains manifest-backed and transport-specific

The Stalwart-backed transport will use:

- Stalwart management API for domain and account provisioning,
- JMAP as the primary mailbox automation surface for `check`, `send`, and `reply`,
- SMTP and IMAP as compatibility or debugging surfaces rather than the primary automation contract.

The gateway will continue to resolve mailbox support from the runtime-owned session manifest referenced by `attach.json.manifest_path`. For mailbox-enabled sessions, it will construct one transport adapter from the resolved mailbox binding:

- filesystem adapter for existing filesystem transport behavior,
- Stalwart adapter for the new real email transport.

If the manifest is missing, unreadable, or lacks a mailbox binding, mailbox routes fail explicitly rather than pretending mailbox support exists.

Why:

- Provisioning and mailbox operations are separate concerns and should use the server surface designed for each.
- JMAP is better aligned with structured mailbox operations than scraping IMAP state or mixing SMTP send with IMAP reads.
- IMAP and SMTP remain useful for manual inspection and interoperability testing.
- Reusing the manifest-backed mailbox binding keeps one runtime-owned source of truth for mailbox capability across direct runtime flows and gateway-attached flows.

Alternatives considered:

- IMAP plus SMTP as the primary programmatic interface. Rejected because it is more stateful, less structured, and more cumbersome for precise mailbox automation.
- SMTP submission only with no mailbox read API. Rejected because Houmao needs mailbox read or unread and reply workflows, not just outbound delivery.

### Decision 5: Keep the current session-facing `mail` UX while letting mailbox skills prefer the live gateway facade

Houmao will keep the existing operator-facing `mail check`, `mail send`, and `mail reply` command surface plus structured mailbox results. The runtime continues to resolve mailbox support from the session binding and to persist that binding in the manifest.

Projected mailbox system skills and runtime-owned mailbox prompts should prefer the live gateway mailbox facade for shared mailbox operations when a live gateway is attached. When no live gateway is available, sessions may still use direct transport-specific mailbox behavior appropriate to the selected transport.

That means the first shared abstraction boundary for managed agents becomes:

```text
managed agent
    |
    +-- if live gateway exists --> gateway /v1/mail/*
    |
    +-- otherwise -------------> direct transport-specific mailbox path
```

Why:

- This preserves the current runtime control model and avoids making gateway attachment mandatory.
- Agents can use one small transport-neutral API when a gateway is available without losing the ability to work directly when no gateway exists.
- The runtime keeps one consistent operator-facing mailbox UX while the implementation path can evolve.

Alternatives considered:

- Move all mailbox behavior into a gateway-only model immediately. Rejected because existing direct mailbox flows remain useful and gateway attachment is still optional.

### Decision 6: Gateway notifier unread detection uses the shared gateway mailbox facade

The gateway mail notifier will inspect unread state through the same gateway mailbox facade used for `check` behavior instead of reading filesystem mailbox-local SQLite directly.

The notifier keeps its existing busy or idle scheduling rules:

- only enqueue a reminder when request admission is open,
- only enqueue a reminder when no gateway work is actively executing,
- only enqueue a reminder when queue depth is zero.

Unread truth stays transport-owned. Reminder cadence, deduplication metadata, and audit bookkeeping stay gateway-owned.

Why:

- This removes the filesystem-specific SQLite dependency from the notifier path.
- The notifier can use the same unread discovery semantics for both filesystem and Stalwart-backed sessions.
- Gateway-owned bookkeeping remains separate from transport-owned mailbox read state.

Alternatives considered:

- Keep polling unread state from filesystem mailbox-local SQLite and defer transport-generic notifier behavior. Rejected because the gateway would still not abstract mailbox transport differences for managed agents.

### Decision 7: Stalwart credentials stay out of the persisted manifest payload

The persisted session manifest remains secret-free. Stalwart transport bindings in the manifest identify the mailbox transport, participant identity, mailbox address, endpoints, and transport-safe metadata, but they do not persist mailbox secrets inline.

Runtime-managed secret material for Stalwart-backed sessions will need a transport-specific handling path such as session-owned secret files, credential references, or runtime-side secret lookup, while keeping the manifest and shared registry secret-free.

Why:

- The current mailbox manifest contract is intentionally secret-free.
- Real mail transport requires stronger credential handling than a local filesystem path.

Alternatives considered:

- Persist mailbox passwords or tokens in the launch-plan payload. Rejected because it would violate the existing secret-free manifest boundary.

## Architecture

```text
managed agent / runtime-owned mailbox skill
                  |
                  | prefer shared mailbox facade when live
                  v
            Agent Gateway
                  |
      +-----------+-----------+
      |                       |
      | /v1/requests          | /v1/mail/*
      | terminal only         | status/check/send/reply
      |                       |
      +-----------+-----------+
                  |
                  v
        GatewayMailboxFacade
          |              |
          |              +--> StalwartMailboxAdapter
          |                     management API for provisioning
          |                     JMAP for shared mailbox operations
          |
          +--> FilesystemMailboxAdapter
                existing fs mailbox logic
                rules/scripts/sqlite remain transport-local
```

## Gateway Endpoint Inventory

This change touches two classes of gateway endpoints:

- retained gateway endpoints that remain part of the live sidecar surface and continue to support gateway lifecycle, terminal control, or notifier control,
- new shared mailbox endpoints that provide the mailbox abstraction boundary for the mailbox functions common to both the filesystem and `stalwart` transports.

Retained existing endpoints used alongside the mailbox work in this change:

- `GET /health`
- `GET /v1/status`
- `POST /v1/requests`
- `GET /v1/mail-notifier`
- `PUT /v1/mail-notifier`
- `DELETE /v1/mail-notifier`

New gateway mailbox facade endpoints introduced by this change:

- `GET /v1/mail/status`
- `POST /v1/mail/check`
- `POST /v1/mail/send`
- `POST /v1/mail/reply`

Endpoint intent:

- `GET /health`: gateway-local liveness only
- `GET /v1/status`: gateway status for health, connectivity, recovery, admission, and execution state
- `POST /v1/requests`: terminal-mutating work only, still limited to `submit_prompt` and `interrupt`
- `GET|PUT|DELETE /v1/mail-notifier`: notifier control and compact notifier status
- `GET /v1/mail/status`: mailbox availability or support status for the managed session
- `POST /v1/mail/check`: shared mailbox read path for normalized message discovery
- `POST /v1/mail/send`: shared mailbox new-message send path
- `POST /v1/mail/reply`: shared mailbox reply path using opaque message references

## In-Scope Email Functionality

The email and mailbox functionality covered by this change is intentionally limited to the overlap between the filesystem transport and the `stalwart` transport.

Shared mailbox functionality in scope:

- mailbox availability or support status for a managed session
- mailbox message discovery through `check`
- unread-aware mailbox checking through the same shared `check` path
- normalized inbound message metadata suitable for managed-agent or runtime use
- composing and sending a new message
- replying to an existing message through an opaque shared `message_ref`
- attachment handling needed for shared `check`, `send`, and `reply` workflows
- reply ancestry preservation needed to keep replies attached to the correct conversation
- gateway notifier unread polling through the shared mailbox facade instead of direct filesystem SQLite reads
- gateway abstraction of filesystem versus Stalwart transport differences for these shared operations

Normalized message metadata in scope:

- opaque `message_ref`
- optional `thread_ref`
- sender and recipient identities
- `subject`
- body content or body preview appropriate to the operation
- `created_at_utc`
- unread state returned by `check`
- attachment metadata needed by the shared mailbox workflows

Explicitly out of scope for this change even if one transport can support them:

- mailbox folders beyond the shared status or check semantics
- archive, delete, move, or star operations
- gateway-exposed transport administration or provisioning APIs
- filesystem `rules/`, helper scripts, lock files, or SQLite layout as part of the shared gateway contract
- Stalwart-native JMAP object shapes as part of the shared gateway contract

## Risks / Trade-offs

- [Risk] The shared gateway mailbox API is narrower than the underlying transports. → Mitigation: explicitly limit the first shared surface to `status`, `check`, `send`, and `reply`, and defer transport-specific mailbox features to later changes.
- [Risk] Optional gateway attachment means both gateway-backed and direct mailbox paths may coexist. → Mitigation: preserve one runtime-owned mailbox binding source of truth in the manifest and make gateway-backed behavior prefer the same transport-specific semantics rather than inventing a second model.
- [Risk] Opaque `message_ref` handling can become unstable across restarts or transport changes if underspecified. → Mitigation: require stable adapter-owned refs for later `reply` targeting and avoid exposing raw transport ids in the shared contract.
- [Risk] Adding mailbox routes to the existing gateway listener increases surface area on listeners bound to `0.0.0.0`. → Mitigation: keep auth and listener-trust treatment explicit in follow-up design work and avoid making mail routes depend on transport-local secrets in manifests.
- [Risk] Agent-mediated direct Stalwart access introduces mailbox credentials into the launched session boundary when the gateway is absent. → Mitigation: use transport-scoped credentials, keep them out of the manifest, and prefer runtime-managed secret references over plain persisted values.

## Migration Plan

1. Add a new Stalwart-backed transport alongside the existing filesystem transport rather than replacing filesystem mailbox support in place.
2. Add gateway mailbox models and `/v1/mail/*` routes for the shared mailbox operation set.
3. Implement a filesystem gateway mailbox adapter on top of the existing filesystem transport behavior.
4. Implement a Stalwart gateway mailbox adapter using Stalwart provisioning plus JMAP-backed shared mailbox operations.
5. Rewrite gateway notifier unread polling to use the gateway mailbox facade rather than direct filesystem mailbox-local SQLite reads.
6. Update mailbox skills and docs to prefer the live gateway mailbox facade for shared operations while preserving direct transport fallback.
7. Keep existing filesystem mailbox sessions unchanged.

Rollback strategy:

- Disable or stop selecting the Stalwart transport for new sessions.
- Disable or stop using the new gateway `/v1/mail/*` routes and continue using the existing direct mailbox paths.
- Continue using the existing filesystem transport, whose artifacts and tests remain separate.
- No live filesystem mailbox root needs conversion back from Stalwart because this change does not require in-place migration.

## Open Questions

- Should shared gateway mail routes be served only when the gateway listener is on loopback until an explicit auth model exists for broader listeners?
- What exact shape should `message_ref` use in the shared gateway contract: one opaque string, or a small structured object with transport and stability metadata?
- Should runtime `mail check`, `mail send`, and `mail reply` prefer the live gateway facade immediately in this change, or should that preference remain agent-skill-first until a later cleanup?
- Which Stalwart mailbox identifiers should the adapter use internally for stable later `reply` targeting: server-native object ids, RFC-style `Message-ID` headers, or both?
