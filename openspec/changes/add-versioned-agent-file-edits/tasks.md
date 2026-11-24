# Tasks

## 1. Drafts and Revision Storage

- [ ] 1.1 Add Dulwich and the owner-private per-mount repository and SQLite state. Test Git object and commit round trips, published ancestry, candidate retention, and independent home lineages. Exercise the storage API with the Git executable unavailable.
- [ ] 1.2 Implement logical mount paths, bounded tree and file reads, renewable edit leases, and staged create, write, rename, and delete operations. Test lease contention, both rename endpoints, revision-pinned reads, aborted or expired drafts, and an upload that completes after its lease is replaced.
- [ ] 1.3 Validate and freeze a draft into a candidate commit. Return the commit ID and support read-only candidate diffs and published history. Verify logical-agent authorship, target committer identity, anonymous attribution, rejection of supplied author identity, empty directories, lease release, and new rollback commits.

## 2. Shared Gateway Authorization

- [ ] 2.1 Register mount read, edit, and push actions with the PyCasbin authorization subsystem. Test full named and open admin access plus keyed non-admin restrictions by mount and action. Document cross-account logical-agent enrollment and grants through the common CLI.
- [ ] 2.2 Use common SSHSIG proof or valid open authority on the direct target. Test replaced peer keys, source relaunch without re-enrollment, revoked grants, stale target generation or gateway presence, malformed proof, and anonymous lease and open-epoch fencing.

## 3. Publication and Recovery

- [ ] 3.1 Extend owner admission with a durable maintenance claim shared by direct manager input, gateway work, and participating lifecycle operations. Test both prompt-versus-push admission orders across processes, native refusal, gateway loss, and late completions after an owner fences or replaces the earlier execution.
- [ ] 3.2 Implement push validation, expected-commit comparison, and the journaled owner publication handoff with a fake mount adapter. Test stale bases and foreign drift, busy before publication, identical and conflicting operation IDs, and bounded activation evidence. Verify the owner rechecks publisher authority under maintenance and records it separately from commit authorship.
- [ ] 3.3 Recover receipts and published revisions by inspecting recorded intent and projection evidence. Inject crashes before and after the projection switch and lose the response after native handoff. Verify that reads recover publication evidence without replay, unresolved activation retains its guard, and settled readiness releases admission even when freshness is unknown.

## 4. DSH Web Skills Mount

- [ ] 4.1 Provision an owner-enabled private skills mount for qualified DSH Web composition. Register the dedicated provider and keep catalog and file lookups revision-specific. Test collisions with existing skill names, rejection of unsafe paths, provider visibility, and same-home relaunch from a verified retained publication.
- [ ] 4.2 Activate a prepared skill revision through the native maintenance boundary and register the provider in common observation. Test add, metadata and body updates, asset reads, and removal. Verify no broad profile update or MCP restart, unchanged native process and conversation IDs, and zero model calls caused by push. Document the supported activation and effect boundary.

## 5. Gateway and Manager Commands

- [ ] 5.1 Add the typed direct gateway routes for mount discovery, drafts, diff, commit, push, status, and history. Verify the complete HTTP round trip and grant rechecks on read and write. Document the request contract, revision precondition, and which outcomes permit an explicit new attempt.
- [ ] 5.2 Expose `agents single ... files` through the shared caller signer and verified target gateway. Verify signed and open workflows, independent signer and destination selection, compact receipts in text and JSON, and read-only operation lookup after a lost response. Document discovery, editing, pushing, actor provenance, and handling busy or conflict.

## 6. End-to-End Verification

- [ ] 6.1 Exercise two agents under separate provisioned Linux accounts and distinct isolated tmux sockets, with synthetic skills and a controlled local model. Verify an enrolled peer can edit without direct filesystem access or a source gateway. Check that a busy push has no publication and a later authorized push activates the commit for the next qualified load. Verify author and publisher provenance, stale candidate handling, revocation, missing gateway, and replacement-target fencing.
- [ ] 6.2 Run affected Pixi unit and integration suites, lint, type checking, the strict documentation build, and strict OpenSpec validation. Record the qualified DSH build and preset from the native acceptance run.
