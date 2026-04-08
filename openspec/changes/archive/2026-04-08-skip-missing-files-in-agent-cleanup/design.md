## Context

`houmao-mgr agents cleanup session|logs|mailbox` currently routes all target resolution through a valid `manifest.json` load before any cleanup happens. That makes targeted cleanup stricter than the broader runtime janitors: bulk runtime cleanup already treats missing manifests as removable broken envelopes, and the low-level path-removal helper already skips missing paths. In practice, a stopped session envelope may be partial because an operator deleted `manifest.json`, a prior cleanup removed one artifact before failing, or a stale shared-registry record still points at a manifest path that no longer exists.

This change needs to preserve one important safety boundary: cleanup must not widen into guessing or deleting a live managed session just because one manifest file disappeared. The design therefore has to separate "can we identify the runtime-owned session root safely?" from "which cleanup actions still need manifest metadata?".

## Goals / Non-Goals

**Goals:**

- Let managed-session cleanup continue when the runtime-owned session root is known but the manifest is missing, malformed, or stale.
- Preserve live-session blocking when valid local evidence still shows the targeted session as active.
- Make session, logs, and mailbox cleanup evaluate candidate artifacts independently so one missing file does not abort the rest of the cleanup pass.
- Add regression coverage for the damaged-envelope cases that currently raise.

**Non-Goals:**

- Change the public CLI shape of `houmao-mgr agents cleanup`.
- Infer unknown metadata such as `job_dir` from ad hoc filesystem heuristics when the manifest is unavailable.
- Broaden mailbox cleanup beyond session-local `mailbox-secrets/` material.
- Redesign shared-registry publication or tmux identity contracts outside the cleanup path.

## Decisions

### Resolve partial cleanup targets from runtime-owned session roots

The cleanup flow will distinguish between a fully resolved target (valid manifest plus parsed payload) and a partial target (runtime-owned session root recovered safely, but manifest metadata unavailable).

The resolver will accept these partial-target paths:

- explicit `--session-root` when the path matches the runtime-owned session layout,
- explicit `--manifest-path` when the path shape still identifies one runtime-owned `.../manifest.json`, even if that file is missing or malformed,
- fresh shared-registry records whose `runtime.manifest_path` is stale but whose `runtime.session_root` is still present and valid.

If neither a valid manifest nor a runtime-owned session root can be recovered, cleanup will still fail explicitly instead of guessing.

Why this approach:

- It keeps cleanup scoped to Houmao-owned runtime envelopes instead of arbitrary paths.
- It lets operators recover partially deleted stopped sessions without reconstructing manifests first.
- It aligns targeted cleanup with the existing best-effort behavior already used by runtime janitors and low-level path deletion.

Alternative considered:

- Catch `SessionManifestError` at the CLI boundary and return a generic failure.
- Rejected because it preserves the current operator pain: recoverable cleanup work is abandoned even though the remaining session root and disposable artifacts are still known.

### Use best available local evidence for live-session blocking

Session-root deletion will continue to be blocked when the target still appears live, but the design will derive that posture from the best available evidence in this order:

1. valid manifest metadata and its tmux session name,
2. otherwise a fresh shared-registry record whose `runtime.session_root` matches the cleanup target and whose tmux session is still live,
3. otherwise no remaining local evidence that the session still appears live.

This keeps live-session protection in place when Houmao still has authoritative local evidence, while avoiding a hard dependency on one damaged manifest file.

Why this approach:

- It preserves the existing safety posture for normal healthy sessions.
- It uses registry state that Houmao already publishes specifically to locate live runtime-owned envelopes.
- It avoids blocking stopped-session cleanup forever just because the manifest file was deleted first.

Alternatives considered:

- Always allow explicit `--session-root` removal when the manifest is missing.
- Rejected because it weakens live-session safety too much for envelopes that still have fresh shared-registry evidence.

- Always block session-root deletion unless a valid manifest loads.
- Rejected because it makes damaged envelopes permanently uncleanable and defeats the purpose of a cleanup command.

### Make artifact cleanup independent and metadata-aware

Each cleanup command will evaluate its candidate artifacts independently once the session root is resolved:

- `cleanup session` may remove the stopped session root without a valid manifest, but it will only remove `job_dir` when manifest metadata still provides a concrete path.
- `cleanup logs` will continue to work from session-root-relative gateway paths and will treat already-absent log or run-marker files as no-op cleanup work.
- `cleanup mailbox` will target the session-local `mailbox-secrets/` directory directly when present under the resolved session root, without requiring a valid manifest just to confirm that the directory exists.

Missing candidate artifacts will not raise. Metadata-dependent actions whose required metadata is unavailable will be skipped instead of turning the entire cleanup command into an error.

Why this approach:

- It matches the operator expectation for cleanup: remove what is still there, skip what is already gone.
- It avoids coupling the whole cleanup pass to the most fragile artifact in the envelope.
- It keeps the implementation local to the existing cleanup helpers instead of adding a new recovery subsystem.

Alternative considered:

- Preserve the current all-or-nothing behavior where any missing artifact or missing metadata fails the command.
- Rejected because it is exactly the failure mode this change is meant to eliminate.

## Risks / Trade-offs

- [Risk] A damaged live session with no valid manifest but a still-matching fresh registry record could be handled incorrectly if the registry-match logic is incomplete. → Mitigation: prefer manifest-based evidence first, fall back to fresh shared-registry `runtime.session_root` matches, and add regression tests that prove live-session cleanup stays blocked when registry evidence is present.
- [Risk] Mailbox cleanup without a valid manifest could remove a session-local `mailbox-secrets/` directory for a session whose mailbox configuration is otherwise unclear. → Mitigation: keep the scope strictly to `session_root/mailbox-secrets/` and never widen cleanup to runtime-owned credentials or shared mailbox roots.
- [Trade-off] Cleanup results may carry less detail when the manifest is unavailable because metadata such as `job_dir` or tmux session name cannot always be recovered. → Accept because a safe best-effort cleanup result is more valuable than failing damaged-envelope recovery for the sake of perfect metadata.

## Migration Plan

There is no stored-data migration.

Implementation rollout:

1. Extend cleanup target resolution to represent partial session-root-backed targets alongside fully parsed manifest-backed targets.
2. Add live-evidence fallback through fresh shared-registry `runtime.session_root` matching.
3. Update session, logs, and mailbox cleanup helpers to skip missing or metadata-dependent artifacts instead of raising.
4. Add regression tests for missing manifests, stale registry manifest pointers, and already-absent candidate artifacts.
5. Run targeted Pixi cleanup-command tests before applying the change.

Rollback is a code revert of the resolver/helper changes and their tests if the new best-effort behavior proves too permissive.

## Open Questions

- No product-level questions remain for this proposal. The implementation-time check is whether registry-backed stale-manifest fallback should cover only explicit cleanup selectors or also current-session resolution when the current tmux session can still be matched safely through a fresh registry record.
