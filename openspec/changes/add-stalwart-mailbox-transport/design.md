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

Implementation focus is narrower than the full product surface. This change concentrates on the gateway-to-mail-system boundary itself:

- gateway mailbox routes,
- gateway transport adapter behavior,
- gateway notifier polling against transport-backed unread state.

It does not require proving those behaviors through fully launched-agent end-to-end flows. Fabricated gateway attach inputs, manifest-backed mailbox bindings, filesystem mailbox fixtures, and Stalwart mailbox or server fixtures are acceptable for focused implementation and verification in this change.

## Goals / Non-Goals

**Goals:**

- Add a Stalwart-backed mailbox transport that Houmao can configure and use for live mailbox-enabled sessions.
- Treat Stalwart as the source of truth for mailbox delivery, unread state, reply ancestry, and transport-level integrity.
- Add a gateway-owned mailbox facade for the mailbox operations both transports support cleanly: mailbox status, `check`, `send`, and `reply`.
- Keep this change centered on the gateway-versus-email-system interaction layer rather than on launched-agent orchestration.
- Keep a small transport-neutral mailbox contract in Houmao: participant identity, async mailbox participation, explicit reply targeting, operator `mail` UX, and normalized mailbox results.
- Keep mailbox transport behavior runtime-owned through projected mailbox system materials, runtime-managed bindings, and manifest-backed gateway adapter construction.
- Make gateway mail notifier behavior transport-generic by routing unread inspection through the gateway mailbox facade.
- Preserve the existing filesystem transport as a separate transport with its current transport-specific rules.

**Non-Goals:**

- Re-implementing Stalwart semantics in local SQLite, lock files, or a Houmao-managed canonical message corpus.
- In-place migration of an existing live filesystem mailbox root into Stalwart-backed mailboxes.
- Exposing transport-specific mailbox features such as folders, archive, delete, move, or star through the shared gateway API in this change.
- Replacing the existing filesystem transport in this change.
- Requiring fully launched-agent end-to-end flows as the main proof vehicle for the gateway-versus-email-system behavior introduced here.
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

Shared mailbox results will use normalized metadata and plain-string transport-neutral opaque references such as `message_ref` rather than exposing filesystem-local ids, SQLite row identities, or Stalwart-native JMAP object shapes directly.

Callers treat `message_ref` as an opaque string handle. In v1, adapters may encode those handles with transport-prefixed conventions when that keeps later `reply` targeting stateless, but callers do not branch on that encoding and do not interpret transport-local ids from the ref.

Why:

- The filesystem transport and a real email system can both support these operations cleanly.
- Expanding the shared surface to folders, archive, delete, move, or star would force the first gateway abstraction to encode transport-specific semantics too early.
- Opaque references let each transport keep its own authoritative storage identity while still supporting later reply targeting.

Alternatives considered:

- Expose filesystem `message_id` or Stalwart-native ids directly in the shared contract. Rejected because it would leak transport-specific storage assumptions into managed-agent behavior.

### Decision 4: Gateway mailbox adapter construction remains manifest-backed and transport-specific

The Stalwart-backed transport will use:

- Stalwart management API for domain and account provisioning,
- a thin raw-HTTP JMAP client built on the repository's existing synchronous HTTP stack for `check`, `send`, and `reply`,
- SMTP and IMAP as compatibility or debugging surfaces rather than the primary automation contract.

The gateway will continue to resolve mailbox support from the runtime-owned session manifest referenced by `attach.json.manifest_path`. For mailbox-enabled sessions, it will construct one transport adapter from the resolved mailbox binding:

- filesystem adapter for existing filesystem transport behavior,
- Stalwart adapter for the new real email transport.

If the manifest is missing, unreadable, or lacks a mailbox binding, mailbox routes fail explicitly rather than pretending mailbox support exists.

Resolved mailbox bindings stop being one filesystem-shaped dataclass. Instead, the runtime and gateway will use transport-discriminated frozen binding types with shared fields plus transport-specific fields:

- common binding fields: `transport`, `principal_id`, `address`, `bindings_version`
- filesystem binding fields: filesystem mailbox root and other filesystem-only derived data
- Stalwart binding fields: JMAP endpoint or base URL, login identity, and secret-free `credential_ref`

Each transport binding owns its own redacted manifest serialization so persisted launch-plan mailbox data includes only transport-safe fields for that transport.

The gateway mailbox adapter boundary is a small `Protocol` owned by a dedicated gateway mailbox support module adjacent to `gateway_service.py` and `gateway_client.py`. That protocol will define four shared operations for one manifest-backed session binding:

- `status()`
- `check(unread_only, limit, since)`
- `send(...)`
- `reply(message_ref, ...)`

The gateway service constructs at most one adapter per attached managed session from `attach.json -> manifest_path -> launch_plan.mailbox`, caches it for the lifetime of that attached gateway instance, and fails explicitly when no usable adapter can be constructed.

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

That preference is part of this change rather than a later cleanup. Runtime-owned prompt construction and mailbox command readiness checks will dispatch by transport and gateway availability instead of assuming filesystem-only prompt instructions. In practice, the concrete runtime-owned prompt path must update functions such as `prepare_mail_prompt()` and `ensure_mailbox_command_ready()` so filesystem guidance remains filesystem-specific and Stalwart sessions prefer the live gateway facade immediately when it exists.

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

### Decision 7: Stalwart credentials stay out of the persisted manifest payload and flow through secret-free credential references

The persisted session manifest remains secret-free. Stalwart transport bindings in the manifest identify the mailbox transport, participant identity, mailbox address, endpoints, and a secret-free `credential_ref`, but they do not persist mailbox secrets inline.

Runtime-managed secret material for Stalwart-backed sessions is resolved through that `credential_ref` rather than through inline manifest secrets. In v1, that reference may resolve to a runtime-owned credential file under the session root with restrictive permissions. Gateway-backed mailbox access and direct mailbox fallback both use the same session-scoped credential material through the same reference.

Provisioning should reuse existing domains, accounts, and credential material when possible, and it should avoid unnecessary credential rotation unless a later explicit refresh flow is added.

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

## Gateway Mailbox Binding And Adapter Contract

Runtime-owned mailbox binding models in this change become transport-discriminated rather than transport-optional.

Binding expectations:

- `MailboxTransport` expands to `filesystem | stalwart`
- declarative, resolved, and persisted mailbox binding helpers dispatch by transport instead of hard-rejecting every non-filesystem transport
- redacted manifest persistence is transport-specific rather than always serializing `filesystem_root`

Gateway adapter expectations:

- the adapter boundary is a `Protocol`, not an `ABC`
- the protocol lives in a dedicated gateway-mailbox support module so `gateway_service.py` remains the HTTP orchestration layer rather than the transport-implementation home
- gateway HTTP models remain strict Pydantic request or response types; adapters return or consume normalized mailbox values behind that boundary
- the gateway owns adapter selection, lazy construction, caching, and explicit failure behavior for one attached session
- the adapter boundary remains limited to the shared mailbox operation set in this change rather than transport-specific folder or lifecycle features

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

Listener exposure rule for this change:

- `/v1/mail/*` is available only when the gateway listener is loopback-bound
- if the gateway listener is bound to `0.0.0.0`, the mailbox facade reports itself unavailable until an explicit authentication model exists

## Implementation Focus

The intended implementation center of gravity for this change is:

- construct or load a mailbox binding for the gateway,
- route gateway mailbox requests to the correct transport adapter,
- verify shared mailbox behavior against filesystem-backed fixtures and Stalwart-backed fixtures,
- verify notifier unread polling through the same gateway mailbox facade.

The intended implementation center of gravity is not:

- launching or supervising real managed agents as the primary proof path,
- proving prompt-injection or TUI behavior beyond the already existing gateway request surface,
- requiring full runtime session bring-up for every gateway mailbox verification case.

Practical testing and development guidance for this change:

- fabricate `attach.json` plus `manifest.json` inputs when that is the simplest way to exercise gateway mailbox behavior,
- fabricate filesystem mailbox roots and mailbox-local state as needed for filesystem adapter verification,
- fabricate or provision isolated Stalwart test mailboxes and messages as needed for Stalwart adapter verification,
- use a test-scoped Stalwart server fixture or mocked management or JMAP HTTP surfaces as appropriate instead of requiring one globally running Stalwart instance,
- prefer focused gateway-plus-mailbox tests over full end-to-end launched-agent flows.

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
- [Risk] Opaque `message_ref` handling can become unstable across restarts or transport changes if underspecified. → Mitigation: require stable adapter-owned plain-string refs for later `reply` targeting, allow v1 transport-prefixed encodings only as an internal adapter convenience, and avoid exposing raw transport ids in the shared contract.
- [Risk] Adding mailbox routes to the existing gateway listener increases surface area on listeners bound to `0.0.0.0`. → Mitigation: in this change, serve `/v1/mail/*` only on loopback listeners and leave broader listeners mailbox-unavailable until an explicit authentication model exists.
- [Risk] Agent-mediated direct Stalwart access introduces mailbox credentials into the launched session boundary when the gateway is absent. → Mitigation: use transport-scoped credential references, keep secrets out of the manifest, and resolve the underlying credential material from a session-scoped runtime-owned location.

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

- Which Stalwart mailbox identifiers should the adapter use internally for stable later `reply` targeting: server-native object ids, RFC-style `Message-ID` headers, or both?
