# Design

## Context

The existing native refresh reads material already installed in the native home. DSH Web's broad refresh reconciles the effective profile and reloads skill providers and MCP instances. A peer grant for one skill mount requires a narrower activation path. The manager's prompt reservation already serializes owner input across processes. The gateway's current refresh flag is local to its process. [Native Refresh](../../../src/houmao/agents/assets/dsh/managed-refresh.mjs) · [Owner Admission](../../../src/houmao/agents/realm_controller/owner_admission.py)

## Goals / Non-Goals

Use a reusable logical file interface, real Git revision identities, and one owner-controlled publication boundary. The initial deployment is a direct HTTP gateway with an opted-in DSH Web skills mount. The public native refresh route continues to handle material already present in native inputs. Standard Git transport, WebDAV, passive proxying, and additional mount adapters are future integrations.

## Decisions

### Mounts Own File Projection and Activation Scope

Register each mount by an owner-selected adapter, logical name, and private storage identity. A mount adapter defines path and content validation, complete revision preparation, the affected native scope, and read-back evidence. The gateway shares file and edit operations across adapters. For example, a future MCP mount can expose structured declarations with owner-side credential references.

Use canonical relative POSIX names. Allow regular files and directories. Check both endpoints of a rename. Reject traversal, links, reserved names, and collisions with unmanaged resources. Bound signed request bodies, file counts and bytes, drafts, history queries, and retention. Pin a revision for each published-tree read. Store logical content and safe identifiers in history. Native secrets, generated native configuration, and physical paths stay in owner-private projection or control state.

### Edit Over HTTP and Record Git Objects With Dulwich

Use a core route family under `/v1/control/file-edits`. Provide mount discovery, tree and file reads, draft creation and renewal, file and directory operations, diff, commit, abort, push, operation status, and history. Bind the normalized rename destination and push preconditions to the exact request. Reuse bounded body buffering at gateway admission. Return short write receipts with follow-up IDs.

Keep an owner-private bare Dulwich repository for each managed mount. Write blobs, trees, and commits from validated logical files. Empty directories belong to the draft and populated directories follow from committed file paths. Derive Git author from the admitted caller. A verified logical agent is recorded by its approved label and stable identity. An unsigned open call uses explicit anonymous authorship. Use the target gateway's identity as Git committer. The gateway constructs Git-safe identities and records canonical provenance in owner-private bookkeeping. The request supplies the message. Keep saved candidates and published ancestry reachable, including the lineage needed for rollback. Dulwich handles object and ref operations in-process.

Use SQLite for the mount's edit lease and draft metadata, operation journal, and published index. One short renewable lease applies per mount. A durable lease epoch fences stale writes. An unguessable lease capability protects anonymous drafts even when several callers share open admin rights. Bind anonymous operations to the current open epoch and exclude bearer material from audit output. Upload to isolated draft storage and recheck authority and lease in the transaction that installs the completed upload. A commit freezes the draft, then releases its lease. Abort and expiry discard draft edits. Immutable candidates survive editing leases.

### Use Shared Authorization for Mount Operations

Register `files.read`, `files.edit`, and `files.push` on each mount with the shared PyCasbin policy. A keyed target's owner can use the common access commands to enroll a peer's public key and grant individual actions to the logical agent. The principal and grant survive source relaunch and placement changes. The target verifies the enrolled key and exact SSHSIG request. Named admins and users of a valid empty roster receive all registered actions through the common admin role.

The file CLI verifies the target's live gateway and selects the caller credential independently. For example, a caller running `reviewer` as `alice` can sign with its enrolled peer key and edit `writer`'s skills while `writer` runs as `bob`. The target gateway performs file and Git operations under `bob`'s account and records `reviewer` as author. The target needs no source runtime or filesystem access. The actor who later publishes is recorded separately in the push journal and receipt.

Editing requires a verified attached target gateway. Gateway-free mail and direct prompting retain their established routes. An enrolled peer signer can be provisioned before its agent launches. Where both agents share an OS account, the gateway coordinates cooperating callers and shared OS permissions still apply outside it.

### Make Push a Conditional Owner Operation

Push takes a caller-generated operation ID, candidate commit, expected published commit, and target generation. Bind the journal entry to the admitted publisher, including anonymous attribution and the open epoch where applicable, and normalized intent. A caller with current push authority can publish another caller's exact saved commit without changing its author. A repeated ID with the same admitted caller and intent returns the existing receipt. A new attempt after a confirmed busy result uses a new ID. A timeout after possible effects triggers read-only status reconciliation.

1. Validate the candidate and prepare its immutable native projection off-path. Record the attempt and capture the current publication marker. This phase can run while the target is working.
2. Acquire a cross-process owner maintenance reservation that participating ordinary input and lifecycle operations honor. Acquire the adapter's immediate native maintenance boundary for the affected execution and any required native serializer. Keep a durable claim across gateway restarts and release it using attributable settlement and readiness evidence. Confine database transactions to state transitions.
3. Under those claims, verify the publisher's current credential, exact mount permission, and admitted authority, including the qualifying admin entry or open epoch where applicable. Check the target generation and expected base. Confirm the projection marker and prepared revision match the journal. Order policy changes and publication authorization through retained owner state. Give the native operation one owner-controlled publication handoff bound to the operation and target generation.
4. Publish the complete prepared tree by switching one owner-managed revision marker where the adapter qualifies that mechanism. The adapter pins the resolved revision for each read. Activate only the declared native effect scope while maintenance is held. Record the publication and the strongest attributable activation result.

The projection marker is the recovery evidence for which revision became visible on disk. The published index records that result for logical reads. Record prior and candidate markers before the switch and reconcile a crash between marker and index updates under the owner reservation. During unresolved recovery, report the evidence available and refuse competing publication. Native acknowledgement comes from the identified execution. A published marker alone establishes file publication. Release maintenance after native settlement and valid readiness even if some freshness evidence remains unknown. Explicit owner recovery fences the old execution before removing an unresolved claim.

### Qualify a Dedicated DSH Web Skills Provider

Install an opt-in filesystem skill provider in the exact managed agent scope from the existing DSH Web composition hook. Use a distinct, watcher-disabled provider backed by a private versioned directory. Mount its own logical tree, starting from an empty managed revision. The provider retains revision-specific locators across catalog and body reads. Test standard skill-tool visibility and owner access to the native projection before advertising live capability. The local DSH reference implements this provider under `packages/skill/skill-filesystem`. [DSH Web Composition](../../../src/houmao/agents/assets/dsh/managed-web.mjs)

Within `runMaintenance`, check pending interactions and inputs and fence competing native agent activation. Publish the dedicated provider's revision and invalidate its discovery through the qualified native registration mechanism. Account for the provider in existing common-state observation. Verify expected names, origin, and body and asset availability at the next qualified load. The provider API can invalidate a catalog cache used by other providers, so live qualification must establish the actual activation scope. Keep broad profile reconciliation and MCP restarts outside this push. Report unavailable before publication if the build, preset, sharing, or effects exceed the qualified boundary.

## Risks / Trade-offs

- Git metadata, the native projection, and activation evidence have independent failure boundaries. The recorded operation and revision marker support recovery and preserve uncertainty where evidence is incomplete.
- Mount revisions can outlive editing sessions. Keep published history, reachable candidates with bounded retention, and referenced native revisions. Reclaim only snapshots with no live, draft, or recovery reference.
- Same-UID shell edits can bypass cooperating writers. Use owner-private storage and execution isolation for managed mounts. Reject detected foreign drift before push.

## Migration Plan

Enable the dedicated mount for eligible DSH Web runs through owner provisioning at launch. Existing skill sources stay outside the managed mount. Retain commits and journals in owner-private storage keyed by target and explicit home lineage. Reattachment recovers the same owner's journal. An ordinary same-home relaunch verifies the retained publication and binds a new provider generation. Fresh homes begin with separate history. Rollback creates and pushes a new commit containing an earlier revision's files.
