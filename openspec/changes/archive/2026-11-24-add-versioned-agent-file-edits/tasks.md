# Tasks

## 1. Drafts and Revision Storage

- [x] 1.1 Add Dulwich and the owner-private per-mount repository and SQLite state. Test Git object and commit round trips, published ancestry, candidate retention, and independent home lineages. Exercise the storage API with the Git executable unavailable.
- [x] 1.2 Implement stable mount IDs, logical paths, bounded reads, renewable edit leases, and staged create, write, rename, and delete. Bind signed drafts to the verified actor kind and principal. Test contention, both rename endpoints, revision-pinned reads, abort and expiry, late uploads, and a fresh authorized request from a replacement key on a current lease.
- [x] 1.3 Validate and freeze a draft into a candidate commit. Return the commit ID and support read-only candidate diffs and published history. Verify logical-agent authorship, target committer identity, anonymous attribution, rejection of supplied author identity, empty directories, lease release, and new rollback commits.

## 2. Shared Gateway Authorization

- [x] 2.1 Register the exact `files:<mount-id>` resource and supported actions in the retained gateway authorization catalog. Test named and open admin parity, keyed grant isolation by mount and action, filtered discovery, and replacement mounts that reuse a display name. Document cross-account enrollment, exact grants, and offline inspection through the common `access` CLI.
- [x] 2.2 Reuse SSHSIG v2 and valid open admission for direct target requests. Refuse relay and backing-service proof. Test source relaunch, replaced peer keys, grant revocation and expiry, stale target or listener, invalid proof, signed and unsigned open-epoch transitions, and anonymous lease capabilities.

## 3. Publication and Recovery

- [x] 3.1 Extend owner admission with a durable maintenance claim shared by direct manager input, gateway work, and participating lifecycle operations. Test both prompt-versus-push admission orders across processes, native refusal, gateway loss, and late completions after an owner fences or replaces the earlier execution.
- [x] 3.2 Implement push validation, expected-commit comparison, and publication handoff with a fake mount adapter. Record intent and its deterministic handoff ID before the shared policy handoff under maintenance. Test named-admin demotion, scoped revocation, a handoff that wins the race with revocation, stale bases, foreign drift, busy targets, identical and conflicting operation IDs, bounded activation evidence, and publisher attribution separate from commit authorship.
- [x] 3.3 Recover receipts and published revisions by reconciling the recorded intent, shared handoff, and projection evidence. Inject failure after the policy handoff and before journal settlement, as well as before and after the projection switch and after native dispatch. Verify recovery never replays work, unresolved activation retains its guard, and settled readiness releases admission even when freshness is unknown.

## 4. DSH Web Skills Mount

- [x] 4.1 Provision an owner-enabled private skills mount for qualified DSH Web composition. Register the dedicated provider and keep catalog and file lookups revision-specific. Test collisions with existing skill names, rejection of unsafe paths, provider visibility, and same-home relaunch from a verified retained publication.
- [x] 4.2 Activate a prepared skill revision through the native maintenance boundary and register the provider in common observation. Test add, metadata and body updates, asset reads, and removal. Verify no broad profile update or MCP restart, unchanged native process and conversation IDs, and zero model calls caused by push. Document the supported activation and effect boundary.

## 5. Gateway and Manager Commands

- [x] 5.1 Declare the typed direct file routes in gateway admission and map each to its exact effects. Use explicit shared handoffs at file mutation boundaries and recheck authority before protected disclosure. Test the HTTP round trip, draft ownership, and denial of status lookup with push-only access. Document revision and retry preconditions.
- [x] 5.2 Expose `agents single ... files` through the shared gateway client. Verify owner-local and trusted remote target selection, independent configured or explicit signers, unsigned open requests, compact receipts, and `files.read` status lookup after a lost response. Document discovery, editing, attribution, and busy or conflict outcomes.

## 6. End-to-End Verification

- [x] 6.1 Exercise two agents under separate provisioned Linux accounts and distinct isolated tmux sockets, with synthetic skills and a controlled local model. Verify an enrolled peer can edit without direct filesystem access or a source gateway. Check that a busy push has no publication and a later authorized push activates the commit for the next qualified load. Verify author and publisher provenance, stale candidate handling, revocation, missing gateway, and replacement-target fencing.
- [x] 6.2 Run affected Pixi unit and integration suites, lint, type checking, the strict documentation build, and strict OpenSpec validation. Record the qualified DSH build and preset from the native acceptance run.
