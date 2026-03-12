## Context

`add-agent-mailbox-protocol` introduced a filesystem mailbox transport, runtime-owned mailbox skills, and agent-mediated `mail` commands, but the current implementation still reflects one simplifying assumption: a single `principal_id` is treated as the mailbox owner, the mailbox routing identity, and the concrete mailbox registration key. That assumption shows up in the current code:

- [filesystem.py](/data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/src/gig_agents/mailbox/filesystem.py) stores one `principals` row per `principal_id` and registers in-root mailboxes under `mailboxes/<principal>/`.
- [managed.py](/data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/src/gig_agents/mailbox/managed.py) resolves delivery targets by `principal_id`, keys mutable mailbox state by `principal_id`, and locks under `locks/principals/<principal>.lock`.
- [mailbox_runtime_support.py](/data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/src/gig_agents/agents/mailbox_runtime_support.py) derives `AGENTSYS_MAILBOX_FS_INBOX_DIR` from `principal_id`.
- [cli.py](/data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/src/gig_agents/agents/brain_launch_runtime/cli.py) still accepts arbitrary `--to` strings and still allows prompt-style `--instruction` content for `mail send` and `mail reply`.

That produces four linked problems:

- recipient addressing is ambiguous because short names are accepted even though delivery ultimately needs exact mailbox identity,
- `mail send` and `mail reply` overlap with generic prompt composition instead of behaving like explicit mailbox operations,
- join conflicts only have one implicit behavior instead of explicit `safe`, `force`, and `stash` choices,
- leave-group cleanup is undefined, so operators and agents have no consistent deregistration contract.

Because the mailbox system is still pre-adoption, this design treats the fix as a direct `v1` refactor rather than a compatibility-preserving migration.

```text
CURRENT
principal_id
  ├─ identifies owner
  ├─ identifies recipient
  └─ identifies concrete mailbox path

TARGET
principal_id
  └─ identifies owner

mailbox address
  └─ identifies recipient and routing target

mailbox registration
  └─ binds one address to one concrete mailbox path and lifecycle state
```

## Goals / Non-Goals

**Goals:**

- Make full mailbox address the authoritative routing identity for runtime mail commands and managed delivery.
- Model concrete mailbox directories as lifecycle-managed registrations rather than as an unavoidable one-to-one extension of `principal_id`.
- Enforce “at most one active registration per address” with SQLite-level invariants instead of only Python-side checks.
- Define explicit join conflict handling for `safe`, `force`, and `stash` flows.
- Define explicit leave or deregistration cleanup semantics so mailbox removal is managed rather than improvised.
- Tighten runtime `mail send` and `mail reply` into explicit mailbox-operation surfaces with operator-provided message bodies.
- Publish runtime mailbox env bindings and filesystem layout from active mailbox registrations instead of reconstructing them from `principal_id`.
- Preserve immutable canonical message files and avoid rewriting historical message content during lifecycle transitions.

**Non-Goals:**

- No migration or rollback plan for deployed mailbox roots; old principal-keyed roots are unsupported and should be deleted and re-bootstrapped.
- No bump to the canonical mailbox protocol version constant or “v1” artifact names as part of this refactor.
- No redesign of the canonical Markdown message format beyond clarifying that mailbox addresses are the routing identity.
- No attempt to solve concurrent same-name join races beyond explicit lock-based serialization and explicit failure.
- No introduction of multi-host mailbox discovery, internet mail transport, or automatic nickname-to-address inference.
- No requirement to delete external symlink targets for private mailboxes during destructive cleanup modes.

## Decisions

### 1) This remains the intended `v1` contract, and stale mailbox roots are a hard reset

The refactor keeps the mailbox protocol version at `1` and keeps existing `v1` naming, but it does not preserve compatibility with mailbox roots created by the earlier principal-keyed implementation. Old mailbox roots are unsupported and must be deleted and re-bootstrapped.

When bootstrap or a managed lifecycle operation can clearly detect a stale principal-keyed root, it should fail with an explicit “delete and re-bootstrap mailbox root” error rather than a confusing generic mismatch.

Rationale:

- this repository is still pre-adoption, so hard reset is cheaper than migration machinery,
- `MAILBOX_PROTOCOL_VERSION` currently also gates canonical message parsing in [protocol.py](/data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/src/gig_agents/mailbox/protocol.py), so bumping it would create unrelated churn,
- keeping the version at `1` avoids conflating a registration/storage refactor with a canonical message-envelope change.

Alternatives considered:

- Bump the on-disk protocol version and potentially rename `v1` notes. Rejected because it widens churn without buying meaningful value in a pre-adoption reset workflow.

### 2) Routing identity is mailbox address; `principal_id` is ownership metadata

All operator-facing and managed delivery flows will treat full mailbox address as the recipient routing key. Canonical messages will continue to carry both `principal_id` and `address`, but the address becomes the authoritative delivery identity while `principal_id` describes ownership or agent identity.

Rationale:

- the address is already the most email-like and future-proof identity,
- one principal may need more than one mailbox later,
- strict full-address routing eliminates nickname ambiguity in `mail send`.

Alternatives considered:

- Keep routing by `principal_id` and merely validate nickname syntax more strictly. Rejected because it still couples routing to ownership and keeps multi-mailbox ownership awkward.
- Route only by opaque mailbox UUID. Rejected because operators and agents need readable addressing in CLI and message headers.

### 3) The SQLite model centers on `mailbox_registrations`, not on one row per principal

The current `principals` registry will be replaced with an explicit registration model. The core table shape is:

```text
mailbox_registrations
  registration_id TEXT PRIMARY KEY
  address TEXT NOT NULL
  owner_principal_id TEXT NOT NULL
  status TEXT NOT NULL            -- active | inactive | stashed
  mailbox_kind TEXT NOT NULL      -- in_root | symlink
  mailbox_path TEXT NOT NULL
  display_name TEXT NULL
  manifest_path_hint TEXT NULL
  role TEXT NULL
  created_at_utc TEXT NOT NULL
  deactivated_at_utc TEXT NULL
  replaced_by_registration_id TEXT NULL
```

SQLite will enforce “at most one active registration per address” with a partial unique index on `address` for rows where `status = 'active'`.

Mutable registration-scoped tables will key off `registration_id`, not `principal_id`:

```text
mailbox_projections(registration_id, message_id, folder_name, projection_path, ...)
mailbox_state(registration_id, message_id, is_read, is_starred, ...)
```

These tables should use foreign keys to `mailbox_registrations(registration_id)` with deletion semantics that allow `purge` to remove registration-scoped mutable state cleanly while preserving canonical messages.

Canonical recipient history will stay decoupled from live registrations. The message-recipient catalog should snapshot delivery identity directly in canonical message history, for example by storing recipient address and related ownership snapshot fields alongside `message_id`, rather than depending on a foreign key to a live registration row.

That split is deliberate:

- `mailbox_registrations` models live and historical mailbox artifacts,
- `mailbox_projections` and `mailbox_state` model mutable mailbox views tied to one concrete registration,
- canonical message history remains stable even if the registration later becomes `inactive`, `stashed`, or `purged`.

Rationale:

- `stash` requires the old mailbox artifact to remain representable after a new active mailbox takes over the same address,
- `purge` needs a way to delete registration-scoped mutable state without erasing canonical message history,
- SQLite-enforced uniqueness is more reliable than Python-only checks for concurrent joins.

Alternatives considered:

- Keep one principal row and add stash metadata elsewhere. Rejected because it does not model multiple historical mailbox artifacts cleanly.
- Keep principal-keyed mutable state and use address only as a lookup layer. Rejected because it reintroduces principal-based mailbox identity through the back door.

### 4) Filesystem layout and locking use literal full addresses plus one shared path-segment helper

The filesystem layout will use literal full mailbox addresses for both active mailbox entries and lock names:

```text
mailboxes/<address>/
locks/addresses/<address>.lock
```

There will be no separate encoding layer in `v1`. Instead, the implementation will centralize one shared address-to-path-segment helper that:

- validates the mailbox address as a safe literal path segment,
- rejects unsafe values before they are used as mailbox directory or lock filenames,
- returns the literal full address string when it is safe to use.

That helper will be the only supported way to translate mailbox addresses into filesystem path segments for mailbox directories, address locks, and related runtime bindings.

Address-scoped locks become the authoritative serialization key. Any operation that mutates delivery state, mailbox projections, mailbox registration state, or registration-scoped mutable state will:

1. determine the affected full mailbox addresses,
2. acquire their `locks/addresses/<address>.lock` files in ascending lexicographic address order,
3. then acquire `locks/index.lock`,
4. then perform the SQLite and filesystem mutation.

This applies to delivery, mailbox-state mutation, register, deregister, and repair flows that manipulate registration-scoped artifacts.

Rationale:

- the routing identity is now the mailbox address, so the serialization key should match it,
- one shared helper avoids drifting rules between `mailboxes/` and `locks/`,
- literal full addresses keep operator inspection honest and align with the chosen docs/examples.

Alternatives considered:

- Keep principal-id locks. Rejected because address replacement under `force` or `stash` can race with delivery if the lock key is not the routing identity.
- Encode addresses for directories/locks. Rejected because it adds indirection with no real benefit for the intended local-host filesystem contract.

### 5) Join and leave become explicit managed lifecycle operations with the existing JSON script pattern

The mailbox helper contract under `rules/scripts/` will grow two managed lifecycle operations:

- `register_mailbox.py`
- `deregister_mailbox.py`

Both scripts will follow the same operational pattern as `deliver_message.py`:

- accept `--mailbox-root`,
- accept `--payload-file`,
- load one JSON payload from that file,
- emit exactly one JSON object to stdout.

The `register_mailbox.py` payload will include at minimum:

- `mode`
- `address`
- `owner_principal_id`
- `mailbox_kind`
- `mailbox_path`

and may include optional metadata such as `display_name`, `manifest_path_hint`, and `role`.

Its result object will include at minimum:

- `ok`
- `mode`
- `address`
- `active_registration_id`
- `owner_principal_id`
- `status`

and will include replacement/stash details when applicable, such as `reused_existing`, `replaced_registration_id`, `stashed_registration_id`, or `stashed_mailbox_path`.

The `deregister_mailbox.py` payload will include at minimum:

- `mode`
- `address`

Its result object will include at minimum:

- `ok`
- `mode`
- `address`
- `target_registration_id`
- `resulting_status`

and may include `purged_registration_id` or `deactivated_registration_id` depending on the selected mode.

The runtime bootstrap path remains package-internal and does not shell out to those helpers to bootstrap an empty mailbox root, but when it ensures that the active session mailbox is registered it will apply the same semantic checks as `safe` join.

Rationale:

- these are the exact operational seams currently missing from the protocol,
- mailbox-local managed scripts keep agents from inventing raw SQLite and filesystem mutations,
- reusing the existing `--mailbox-root` plus `--payload-file` pattern fits the repo’s managed mailbox tooling.

Alternatives considered:

- Keep lifecycle operations implicit inside bootstrap only. Rejected because operators and agents also need explicit post-bootstrap cleanup and conflict handling.
- Invent a different CLI contract for lifecycle helpers. Rejected because it would create a second mailbox-local script pattern for no benefit.

### 6) Runtime mail commands and env bindings follow the active mailbox registration

`mail send` and `mail reply` will no longer accept prompt-style `--instruction`. They will require explicit body input through `--body-file` or `--body-content`. `--to` and `--cc` will require full mailbox addresses, not short names.

The prompt payload delivered to the live agent will carry explicit recipient addresses and explicit Markdown body content, not an instruction asking the agent to invent content.

Runtime mailbox bindings will also stop reconstructing paths from `principal_id`. After bootstrap or refresh resolves the active mailbox registration, the runtime will publish bindings from that registration, including `AGENTSYS_MAILBOX_FS_INBOX_DIR` pointing at the active mailbox inbox path rather than at `mailboxes/<principal_id>/inbox`.

Rationale:

- mailbox commands should be deterministic transport operations,
- explicit body content improves automation, testing, and operator clarity,
- address-routed registrations require runtime bindings to follow the concrete registration path, not string concatenation from ownership metadata.

Alternatives considered:

- Keep `--instruction` as an optional convenience flag. Rejected because it preserves overlap with prompt-oriented commands and weakens the mailbox contract.
- Continue deriving inbox paths from `principal_id`. Rejected because it conflicts directly with address-keyed mailbox directories and symlink-backed registrations.

### 7) Historical mailbox artifacts remain attributable without rewriting canonical messages

`stash` and `deactivate` flows will preserve old mailbox artifacts and historical state without modifying canonical message files. A stashed in-root mailbox directory will be renamed by suffixing a UUID4 hex token, for example:

```text
mailboxes/
  AGENTSYS-bob@agents.localhost/
  AGENTSYS-bob@agents.localhost--7f3d2d8d4eb74a6ab5df7b4aef41c3f2/
```

Historical attribution remains understandable through immutable message headers, timestamps, canonical recipient history, and registration history recorded in SQLite. This preserves auditability while allowing a new active mailbox registration to claim the original address.

Rationale:

- avoids rewriting immutable message content,
- makes stash behavior inspectable on disk,
- keeps registration replacement explicit in both filesystem and SQLite state.

Alternatives considered:

- Rewrite historical messages to point at a new identity. Rejected because it violates message immutability.
- Hide stashed state only in SQLite while keeping the old directory name unchanged. Rejected because it obscures the filesystem history and blocks a new active registration from using the original address path.

## Risks / Trade-offs

- [Schema complexity increases] → Keep the registration model narrow, enforce the most important invariant in SQLite, and keep canonical history separate from mutable registration-scoped state.
- [Stale mailbox roots now fail harder] → Make bootstrap and lifecycle helpers emit a clear “delete and re-bootstrap mailbox root” error when they detect the old principal-keyed layout.
- [Address-based path names need stricter validation] → Centralize one shared address-to-path-segment helper and reuse it everywhere address strings become filesystem segments.
- [The runtime still relies on agent-mediated mailbox execution] → Tighten the request payload/result contract so the agent is operating a deterministic mailbox action even though the turn still flows through the prompt surface.
- [Old examples and fixtures become invalid] → Update Q&A, skill references, CLI help, runtime env-binding docs, and tests in the same change so the repo consistently teaches the new contract.

## Migration Plan

No migration plan is required for this change. The mailbox system is still pre-adoption, so the implementation may refactor the on-disk schema, managed-script set, runtime CLI contract, and mailbox registration model directly as the intended `v1` behavior. Old principal-keyed mailbox roots are unsupported and should be deleted and re-bootstrapped.

## Open Questions

- None at proposal time. This design intentionally resolves the current open questions by choosing address-first routing, explicit lifecycle modes, hard-reset handling for stale roots, literal address path segments, address-scoped locks, and explicit body-content inputs.
