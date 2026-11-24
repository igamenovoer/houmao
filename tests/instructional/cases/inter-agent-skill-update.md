# Peer-Authorized Skill Update Through the Versioned Mount

An authorized source agent updates a target DSH Web agent's published `release-notes` skill through the target's `skills` mount. The case proves peer discovery, draft editing, candidate publication with the source agent as publisher, and the target loading the new revision on its next turn.

## Sub-cases

- `inter-agent-create`: the source agent discovers the target mount, creates `release-notes/SKILL.md`, commits, and publishes the first candidate with `publisher.kind=agent` and `principal_id=reviewer`.
- `inter-agent-update`: the source agent reads the current skill, adds a Risks section, saves a second candidate, and publishes it against the first published commit.
- `inter-agent-next-load`: the target's next `release-notes` load resolves the second revision and the output includes the Risks section.
- `inter-agent-missing-push-grant`: after revoking `files.push` from `reviewer`, a source push is refused and the saved candidate remains. This arm is documented but was not exercised in the current self-proof.
- `inter-agent-shadow-conflict`: a candidate whose skill name shadows a visible native skill is refused. This arm is documented but was not exercised in the current self-proof.

## How to get to it (user POV)

- Prepare a target DSH Web agent with `managed_web_skills: true` and a separate source DSH Web agent.
- On the target, enroll the source's public key as the `reviewer` principal and grant `files.read`, `files.edit`, and `files.push` on the exact `skills` mount.
- Give the source agent a peer brief with the target agent ID, gateway URL, context ID, generation, and presence.
- Send the source an ordinary operator request to create or update the target's skill.
- The source uses the installed Houmao skills and `houmao-mgr agents single ... files` with its configured peer signer and the target's remote coordinates.
- Verify the target's published tree and prompt the target to use the skill.

## Driving it with skill_update_lab.py and houmao-mgr

Preconditions:

- Run the README Launch section and keep `$RUN_TMP`, `$RUN_META`, `$REPO_ROOT`, and `$HOUMAO_MGR` exported.
- `python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" doctor --run-meta "$RUN_META"` exits zero.
- The target's `skills` mount is visible and `reviewer` has active `files.read`, `files.edit`, and `files.push` grants.
- The source's `peer-brief.json` exists at `$SOURCE_RUN/workdir/peer-brief.json` and contains the target coordinates, not the mount ID.

- **Create the first candidate.** Send:

  ```bash
  python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" prompt \
    --run-meta "$RUN_META" --role source \
    --prompt "Read the peer brief at $SOURCE_RUN/workdir/peer-brief.json. Create a release-notes skill on the target agent's versioned mount. Its instructions should say: produce a one-line summary, a list of changed files, and a short verification note. Use your configured peer signer, discover the target mount, publish one candidate, and report the push receipt."
  ```

  The source transcript must show `files mounts` with the remote `--url`, `--context-id`, `--generation`, and `--presence` plus `--self-signer`; a lease open; `write release-notes/SKILL.md`; a commit; and a push. The receipt must report `outcome=published`, `publisher.kind=agent`, `publisher.principal_id=reviewer`, `activation=effective`, and `native_ready=true`.

- **Capture the first published commit.** Find the source session and extract the last published push receipt:

  ```bash
  export SOURCE_SESSION="$(find "$SOURCE_RUN/runtime/homes" -path '*/sessions/*/session.v4.jsonl' -type f | head -1)"
  jq -c 'select(.type=="tool/result" and ((.data.message.content[0].text // "") | contains("\"outcome\": \"published\"")))' "$SOURCE_SESSION" | tail -1 > "$RUN_TMP/evidence/inter-agent-skill-update/create-push-line.json"
  jq -r '.data.message.content[0].text' "$RUN_TMP/evidence/inter-agent-skill-update/create-push-line.json" > "$RUN_TMP/evidence/inter-agent-skill-update/create-push.json"
  export BASE_COMMIT="$(jq -r '.published_commit' "$RUN_TMP/evidence/inter-agent-skill-update/create-push.json")"
  ```

- **Update the same skill.** Send:

  ```bash
  python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" prompt \
    --run-meta "$RUN_META" --role source \
    --prompt "Read the peer brief at $SOURCE_RUN/workdir/peer-brief.json. Update the target agent's release-notes skill so it also includes a short Risks section after the verification note. Use your configured peer signer, discover the target mount, publish one candidate, and report the push receipt."
  ```

  The source must open the new draft against `BASE_COMMIT`, read the current file, write the modified file, commit, and push. Capture the second receipt and set the published revision:

  ```bash
  jq -c 'select(.type=="tool/result" and ((.data.message.content[0].text // "") | contains("\"outcome\": \"published\"")))' "$SOURCE_SESSION" | tail -1 > "$RUN_TMP/evidence/inter-agent-skill-update/update-push-line.json"
  jq -r '.data.message.content[0].text' "$RUN_TMP/evidence/inter-agent-skill-update/update-push-line.json" > "$RUN_TMP/evidence/inter-agent-skill-update/update-push.json"
  export PUBLISHED_COMMIT="$(jq -r '.published_commit' "$RUN_TMP/evidence/inter-agent-skill-update/update-push.json")"
  ```

  The second receipt must report `outcome=published`, a different `published_commit`, `activation=effective`, and `native_ready=true`.

- **Read-only cross-check.** Read the file at the second published revision:

  ```bash
  python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" read \
    --run-meta "$RUN_META" --path release-notes/SKILL.md --revision "$PUBLISHED_COMMIT"
  ```

  Decode `content_base64` and confirm the Risks line is present. Also list the mount and confirm `published_commit` matches the receipt.

- **Verify the target load.** Send:

  ```bash
  python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" prompt \
    --run-meta "$RUN_META" --role target \
    --prompt "Use the release-notes skill to draft release notes for adding a new --dry-run flag. Changed files: src/app/cli.py. Keep it short and include the Risks section."
  ```

  In the target transcript, the `skill` tool result for `release-notes` must show a base directory ending in the second published revision and instructions containing the Risks line. The final assistant output must include the Risks section.

- **Guardrail arm: missing push grant.** Resolve the target run and agent ID, then revoke only `files.push` from `reviewer`:

  ```bash
  export TARGET_RUN="$(jq -r '.target_run' "$RUN_META")"
  export TARGET_AGENT="$(jq -r '.target_agent_id' "$RUN_META")"
  HOUMAO_GLOBAL_REGISTRY_DIR="$TARGET_RUN/registry" \
  HOUMAO_GLOBAL_RUNTIME_DIR="$TARGET_RUN/runtime" \
  HOUMAO_PROJECT_OVERLAY_DIR="$TARGET_RUN/workdir/.houmao" \
  HOUMAO_GLOBAL_MAILBOX_DIR="$TARGET_RUN/workdir/.houmao/mailbox" \
    "$HOUMAO_MGR" --print-json agents single --agent-id "$TARGET_AGENT" \
    access revoke reviewer "files:$MOUNT_ID" files.push
  ```

  Ask the source to update the skill again. The push must be refused; the candidate must remain saved and the published revision must not change. Restore the grant afterward:

  ```bash
  HOUMAO_GLOBAL_REGISTRY_DIR="$TARGET_RUN/registry" \
  HOUMAO_GLOBAL_RUNTIME_DIR="$TARGET_RUN/runtime" \
  HOUMAO_PROJECT_OVERLAY_DIR="$TARGET_RUN/workdir/.houmao" \
  HOUMAO_GLOBAL_MAILBOX_DIR="$TARGET_RUN/workdir/.houmao/mailbox" \
    "$HOUMAO_MGR" --print-json agents single --agent-id "$TARGET_AGENT" \
    access grant reviewer "files:$MOUNT_ID" files.push
  ```

  This arm was not exercised in the current self-proof; verify the exact refusal outcome before treating it as proven.

- **Guardrail arm: shadow conflict.** Ask the source to create a skill whose name matches a visible native skill, such as `houmao-agent-entrypoint`. The target mount must refuse the candidate because it would shadow a native skill. This arm was not exercised in the current self-proof; verify the exact refusal outcome before treating it as proven.

- **Proof.** Save the source transcript, both push receipts, the `read` payload, the target skill tool result, and `final-assistant.txt` under `$RUN_TMP/evidence/inter-agent-skill-update/`. Confirm each file exists after cleanup.

## Gotchas

- The source and target do not share a registry. The source must use the target's `--url`, `--context-id`, `--generation`, `--presence`, and `--self-signer`; do not use a local `agents self` command against the peer.
- The mount ID is discovered with `files mounts`, not inferred from the peer brief or a display name.
- The mount starts empty; the first candidate creates the skill. A candidate that shadows a visible native skill is refused.
- A push can return `busy` when the target is active. The candidate stays saved; retry only after readiness with a fresh operation ID.
- `publisher` and `author` are separate. A source agent that publishes a candidate is the publisher; the commit author is the principal that committed the draft.
- The target's native skill tool may resolve the new revision while an already-open browser tab shows a stale catalog. Reload the tab; do not treat the stale tab as a failed publication.

## Blinding and Transcript Checks

- The prompts are ordinary operator requests. Do not include evaluation, judging, benchmark, or candidate vocabulary in prompts seen by the source or target.
- Grade from the source's actual `files` tool calls, the push receipts, the target mount state, and the target skill tool result. The source's final summary is supporting evidence only.
- Do not leave a narrow smoke-test role active; use the general source role from `helpers/roles/skill-source.md`.
