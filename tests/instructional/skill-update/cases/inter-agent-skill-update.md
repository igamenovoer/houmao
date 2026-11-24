# Peer-Authorized Skill Update Through the Versioned Mount

An authorized source agent updates a target DSH Web agent's published `release-notes` skill through the target's `skills` mount. The case proves peer discovery, draft editing, candidate publication with the source agent as publisher, and the target loading the new revision on its next turn.

## Sub-cases

- `inter-agent-create`: the source agent discovers the target mount, creates `release-notes/SKILL.md`, commits, and publishes the first candidate with `publisher.kind=agent` and `principal_id=reviewer`.
- `inter-agent-update`: the source agent reads the current skill, adds a Risks section, saves a second candidate, and publishes it against the first published commit.
- `inter-agent-next-load`: the target's next `release-notes` load resolves the second revision and the output includes the Risks section.
- `inter-agent-missing-push-grant`: the target's open roster is closed with a first admin key, then `files.push` is revoked from `reviewer`; a source push is refused, the saved candidate remains, and the published revision does not change.
- `inter-agent-shadow-conflict`: a candidate whose skill name shadows a visible native skill is refused with `outcome=conflict`, `reason=file_native_conflict`, and the published revision stays unchanged.

## How to get to it (user POV)

- Prepare a target DSH Web agent with `managed_web_skills: true` and a separate source DSH Web agent.
- On the target, enroll the source's public key as the `reviewer` principal and grant `files.read`, `files.edit`, and `files.push` on the exact `skills` mount.
- Give the source agent a peer brief with the target agent ID, gateway URL, context ID, generation, and presence.
- Send the source an ordinary operator request to create or update the target's skill.
- The source uses the installed Houmao skills and `houmao-mgr agents single ... files` with its configured peer signer and the target's remote coordinates.
- Verify the target's published tree and prompt the target to use the skill.

## Driving it with skill_update_lab.py and houmao-mgr

Preconditions:

- Run the bundle `README.md` Launch section and keep `$RUN_TMP`, `$RUN_META`, `$REPO_ROOT`, `$BUNDLE_ROOT`, and `$HOUMAO_MGR` exported.
- `python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" doctor --run-meta "$RUN_META"` exits zero.
- The target's `skills` mount is visible and `reviewer` has active `files.read`, `files.edit`, and `files.push` grants.
- The source's `peer-brief.json` exists at `$SOURCE_RUN/workdir/peer-brief.json` and contains the target coordinates, not the mount ID.
- Run the create/update/load steps before the keyed missing-grant arm. The intra-agent case should run before the roster is keyed if it relies on the owner-publish shortcut.

- **Create the first candidate.** Send:

  ```bash
  mkdir -p "$RUN_TMP/evidence/skill-update/inter-agent-skill-update"
  python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" prompt \
    --run-meta "$RUN_META" --role source \
    --prompt "Read the peer brief at $SOURCE_RUN/workdir/peer-brief.json. Create a release-notes skill on the target agent's versioned mount. Its instructions should say: produce a one-line summary, a list of changed files, and a short verification note. Use your configured peer signer, discover the target mount, publish one candidate, and report the push receipt."
  ```

  The source transcript must show `files mounts` with the remote `--url`, `--context-id`, `--generation`, and `--presence` plus `--self-signer`; a lease open; `write release-notes/SKILL.md`; a commit; and a push. The receipt must report `outcome=published`, `publisher.kind=agent`, `publisher.principal_id=reviewer`, `activation=effective`, and `native_ready=true`.

- **Capture the first published commit.** Copy the source session and extract the last published push receipt cleanly (even when shell output wraps the JSON):

  ```bash
  export SOURCE_SESSION="$(find "$SOURCE_RUN/runtime/homes" -path '*/sessions/*/session.v4.jsonl' -type f | head -1)"
  cp "$SOURCE_SESSION" "$RUN_TMP/evidence/skill-update/inter-agent-skill-update/source-session.v4.jsonl"
  python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" extract-push \
    --run-meta "$RUN_META" --role source --outcomes published \
    > "$RUN_TMP/evidence/skill-update/inter-agent-skill-update/create-push.json"
  export BASE_COMMIT="$(jq -r '.published_commit' "$RUN_TMP/evidence/skill-update/inter-agent-skill-update/create-push.json")"
  ```

- **Update the same skill.** Send:

  ```bash
  python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" prompt \
    --run-meta "$RUN_META" --role source \
    --prompt "Read the peer brief at $SOURCE_RUN/workdir/peer-brief.json. Update the target agent's release-notes skill so it also includes a short Risks section after the verification note. Use your configured peer signer, discover the target mount, publish one candidate, and report the push receipt."
  ```

  The source must open the new draft against `BASE_COMMIT`, read the current file, write the modified file, commit, and push. Capture the second receipt and set the published revision:

  ```bash
  cp "$SOURCE_SESSION" "$RUN_TMP/evidence/skill-update/inter-agent-skill-update/source-session.v4.jsonl"
  python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" extract-push \
    --run-meta "$RUN_META" --role source --outcomes published \
    > "$RUN_TMP/evidence/skill-update/inter-agent-skill-update/update-push.json"
  export PUBLISHED_COMMIT="$(jq -r '.published_commit' "$RUN_TMP/evidence/skill-update/inter-agent-skill-update/update-push.json")"
  ```

  The second receipt must report `outcome=published`, a different `published_commit`, `activation=effective`, and `native_ready=true`.

- **Read-only cross-check.** Read the file at the second published revision:

  ```bash
  python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" read \
    --run-meta "$RUN_META" --path release-notes/SKILL.md --revision "$PUBLISHED_COMMIT" \
    > "$RUN_TMP/evidence/skill-update/inter-agent-skill-update/read.json"
  ```

  Decode `content_base64` and confirm the Risks line is present. Also list the mount and confirm `published_commit` matches the receipt.

- **Verify the target load.** Send:

  ```bash
  python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" prompt \
    --run-meta "$RUN_META" --role target \
    --prompt "Use the release-notes skill to draft release notes for adding a new --dry-run flag. Changed files: src/app/cli.py. Keep it short and include the Risks section."
  ```

  In the target transcript, the `skill` tool result for `release-notes` must show a base directory ending in the second published revision and instructions containing the Risks line. The final assistant output must include the Risks section.

- **Guardrail arm: missing push grant.** A freshly launched target has an empty admin roster and runs in `admin_mode=open`, where every reachable key has all client-facing permissions; revoking a direct grant does not deny anything. Close the roster with a dedicated first admin key before revoking:

  ```bash
  python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" key-admin --run-meta "$RUN_META" \
    > "$RUN_TMP/evidence/skill-update/inter-agent-skill-update/key-admin.json"
  ```

  The helper creates `$RUN_TMP/runtime/keys/target-admin`, enrolls it with `access admin-add --first`, and verifies that `access explain` reports `admin_mode=keyed`. Confirm the reviewer's other grants are still active, then revoke only the push grant:

  ```bash
  export TARGET_RUN="$(jq -r '.target_run' "$RUN_META")"
  export TARGET_AGENT="$(jq -r '.target_agent_id' "$RUN_META")"
  HOUMAO_GLOBAL_REGISTRY_DIR="$TARGET_RUN/registry" \
  HOUMAO_GLOBAL_RUNTIME_DIR="$TARGET_RUN/runtime" \
  HOUMAO_PROJECT_OVERLAY_DIR="$TARGET_RUN/workdir/.houmao" \
  HOUMAO_GLOBAL_MAILBOX_DIR="$TARGET_RUN/workdir/.houmao/mailbox" \
    "$HOUMAO_MGR" --print-json agents single --agent-id "$TARGET_AGENT" \
    access revoke reviewer "files:$MOUNT_ID" files.push
  HOUMAO_GLOBAL_REGISTRY_DIR="$TARGET_RUN/registry" \
  HOUMAO_GLOBAL_RUNTIME_DIR="$TARGET_RUN/runtime" \
  HOUMAO_PROJECT_OVERLAY_DIR="$TARGET_RUN/workdir/.houmao" \
  HOUMAO_GLOBAL_MAILBOX_DIR="$TARGET_RUN/workdir/.houmao/mailbox" \
    "$HOUMAO_MGR" --print-json agents single --agent-id "$TARGET_AGENT" \
    access explain reviewer "files:$MOUNT_ID" files.push \
    > "$RUN_TMP/evidence/skill-update/inter-agent-skill-update/deny-explain.json"
  ```

  `access explain` must now report `admin_mode=keyed`, `direct_grant=null`, and a non-allowed decision for `files.push`; the default `agent-requester` group does not include that action. Ask the source to update the skill again. Expect a refusal rather than a published receipt. In the current build the CLI reports `HTTP 403` and `access explain` reports `allowed: false` with `reason: insufficient_authority`; capture the raw output, confirm `published_commit` and the mount revision are unchanged, and confirm the candidate commit remains saved.

  A keyed roster also requires a signer for mount reads. Use the enrolled admin key to prove the unchanged revision:

  ```bash
  export ADMIN_KEY="$(jq -r '.admin_key_path' "$RUN_META")"
  python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" mounts --run-meta "$RUN_META" \
    --signer "$ADMIN_KEY" > "$RUN_TMP/evidence/skill-update/inter-agent-skill-update/mounts-after-denial.json"
  ```

  The `published_commit` in that payload must still equal the revision from before the revoke. The denied candidate must still appear in the retained history:

  ```bash
  HOUMAO_GLOBAL_REGISTRY_DIR="$TARGET_RUN/registry" \
  HOUMAO_GLOBAL_RUNTIME_DIR="$TARGET_RUN/runtime" \
  HOUMAO_PROJECT_OVERLAY_DIR="$TARGET_RUN/workdir/.houmao" \
  HOUMAO_GLOBAL_MAILBOX_DIR="$TARGET_RUN/workdir/.houmao/mailbox" \
    "$HOUMAO_MGR" --print-json agents single --agent-id "$TARGET_AGENT" \
    files --signer "$ADMIN_KEY" --mount "$MOUNT_ID" history --candidates \
    > "$RUN_TMP/evidence/skill-update/inter-agent-skill-update/candidate-history.json"
  ```

  The candidate commit's `parent` must equal the pre-revoke published revision.

  Restore the grant afterward:

  ```bash
  HOUMAO_GLOBAL_REGISTRY_DIR="$TARGET_RUN/registry" \
  HOUMAO_GLOBAL_RUNTIME_DIR="$TARGET_RUN/runtime" \
  HOUMAO_PROJECT_OVERLAY_DIR="$TARGET_RUN/workdir/.houmao" \
  HOUMAO_GLOBAL_MAILBOX_DIR="$TARGET_RUN/workdir/.houmao/mailbox" \
    "$HOUMAO_MGR" --print-json agents single --agent-id "$TARGET_AGENT" \
    access grant reviewer "files:$MOUNT_ID" files.push
  ```

  Run this arm after the intra-agent case so the owner-publish shortcut still works on an open roster. If a later owner publish must run while the roster is keyed, pass the enrolled admin key through `push-owner --signer` or the raw `files push --signer` path; `push-owner` without a signer assumes an open roster.

- **Guardrail arm: shadow conflict.** Ask the source to create a skill whose name matches a visible native skill, such as `houmao-agent-entrypoint`. The target mount refuses the candidate with `outcome=conflict` and `reason=file_native_conflict`; the published revision and mount contents stay unchanged. Capture the conflict receipt and a 404 read of the shadow path.

- **Proof.** Save the source transcript, both push receipts, the `read` payload, the target skill tool result, and `final-assistant.txt` under `$RUN_TMP/evidence/skill-update/inter-agent-skill-update/`. Confirm each file exists after cleanup.

## Gotchas

- The source and target do not share a registry. The source must use the target's `--url`, `--context-id`, `--generation`, `--presence`, and `--self-signer`; do not use a local `agents self` command against the peer.
- The mount ID is discovered with `files mounts`, not inferred from the peer brief or a display name.
- The mount starts empty; the first candidate creates the skill. A candidate that shadows a visible native skill is refused.
- A push can return `busy` when the target is active. The candidate stays saved; retry only after readiness with a fresh operation ID.
- `publisher` and `author` are separate. A source agent that publishes a candidate is the publisher; the commit author is the principal that committed the draft.
- The target's native skill tool may resolve the new revision while an already-open browser tab shows a stale catalog. Reload the tab; do not treat the stale tab as a failed publication.
- A fresh target starts in `admin_mode=open`; revoking a direct grant does not deny a peer until the roster is keyed with `access admin-add --first`.
- Close the roster only for the missing-grant arm. Run that arm after the intra-agent case, or supply the enrolled admin key to any owner publish that follows.

## Blinding and Transcript Checks

- The prompts are ordinary operator requests. Do not include evaluation, judging, benchmark, or candidate vocabulary in prompts seen by the source or target.
- Grade from the source's actual `files` tool calls, the push receipts, the target mount state, and the target skill tool result. The source's final summary is supporting evidence only.
- Do not leave a narrow smoke-test role active; use the general source role from `helpers/roles/skill-source.md`.
