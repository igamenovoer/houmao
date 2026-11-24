# Agent Self-Update Through Its Own Versioned Skills Mount

A managed DSH Web agent updates its own published `release-notes` skill through the authorized `skills` mount. The case proves the draft and commit path, the documented busy refusal when the agent tries to publish during its own active turn, the owner recovery publish after the turn, and the agent loading the new revision on its next turn.

## Sub-cases

- `intra-agent-draft`: the agent discovers its `skills` mount, opens a lease against the published base, stages a change to `release-notes/SKILL.md`, and saves a candidate commit with itself as author.
- `intra-agent-busy-refusal`: a self-push while the agent is active returns `outcome=busy`, `reason=owner_maintenance_unavailable`, with no published or effective commit and the candidate still saved.
- `intra-agent-owner-publish`: after the target is idle, an authorized owner publishes the exact saved candidate; the receipt reports `outcome=published`, `activation=effective`, and `native_ready=true`.
- `intra-agent-next-load`: the target's next `release-notes` load resolves the new revision path and the resulting output includes the new section.

## How to get to it (user POV)

- Prepare a target DSH Web agent with `managed_web_skills: true`, prompt mode `as_is`, and native permission defaults.
- Configure the target's own peer signer, enroll it as the `self-editor` principal, and grant `files.read`, `files.edit`, and `files.push` on its exact `skills` mount.
- Send the target an ordinary operator request to update its own `release-notes` skill.
- The agent uses the installed Houmao skills and `houmao-mgr agents single ... files` with `--self-signer`.
- If the self-push is busy, publish the saved candidate from the owner context after the agent's turn ends, then ask the agent to use the skill again.

## Driving it with skill_update_lab.py and houmao-mgr

Preconditions:

- Run the README Launch section and keep `$RUN_TMP`, `$RUN_META`, `$REPO_ROOT`, and `$HOUMAO_MGR` exported.
- `python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" doctor --run-meta "$RUN_META"` exits zero.
- The target's `skills` mount is visible and `self-editor` has an active `files.push` grant.
- The target's native sandbox is `workspace-write`; do not edit `<home>/skills` directly. This case uses only the versioned mount.

- **Send the self-update request.** Run:

  ```bash
  python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" prompt \
    --run-meta "$RUN_META" --role target \
    --prompt "Update your own release-notes skill so it also asks for a short Testing section after the Risks section. Use your configured peer signer and the versioned skill mount. Discover the mount, publish one candidate, and report the push receipt."
  ```

  The prompt receipt must report `delivery_state=completed` and `success=true`.

- **Inspect the agent transcript.** Find the target session and confirm the tool calls use `agents single --agent-id <target> files --self-signer`, discover the mount, open a lease, read and write `release-notes/SKILL.md`, show the diff, commit, and push. Save the selected lines under `$RUN_TMP/evidence/intra-agent-skill-update/target-session.v4.jsonl`.

  ```bash
  export TARGET_RUN="$(jq -r '.target_run' "$RUN_META")"
  find "$TARGET_RUN/runtime/homes" -path '*/sessions/*/session.v4.jsonl' -type f
  ```

- **Capture the first push receipt.** Find the target session and extract the last published-or-busy push receipt, then set the candidate and base variables:

  ```bash
  export TARGET_SESSION="$(find "$TARGET_RUN/runtime/homes" -path '*/sessions/*/session.v4.jsonl' -type f | head -1)"
  jq -c 'select(.type=="tool/result" and ((.data.message.content[0].text // "") | (contains("\"outcome\": \"published\"") or contains("\"outcome\": \"busy\""))))' "$TARGET_SESSION" | tail -1 > "$RUN_TMP/evidence/intra-agent-skill-update/push-line.json"
  jq -r '.data.message.content[0].text' "$RUN_TMP/evidence/intra-agent-skill-update/push-line.json" > "$RUN_TMP/evidence/intra-agent-skill-update/push-receipt.json"
  export CANDIDATE_COMMIT="$(jq -r '.candidate' "$RUN_TMP/evidence/intra-agent-skill-update/push-receipt.json")"
  export BASE_COMMIT="$(jq -r '.expected_base' "$RUN_TMP/evidence/intra-agent-skill-update/push-receipt.json")"
  ```

  If the receipt is `outcome=published`, run `export PUBLISHED_COMMIT="$(jq -r '.published_commit' "$RUN_TMP/evidence/intra-agent-skill-update/push-receipt.json")"` and go to the next-load step. If it is `outcome=busy`, the expected reason is `owner_maintenance_unavailable` and both `published_commit` and `effective_commit` must be null. Do not retry inside the same turn.

- **Wait for idle and publish the saved candidate.** Confirm the target is idle:

  ```bash
  python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" state \
    --run-meta "$RUN_META" --role target
  ```

  Require `control.can_accept_prompt_now=true` and `gateway.gateway_health=healthy`. Then publish the exact candidate against its recorded base:

  ```bash
  python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" push-owner \
    --run-meta "$RUN_META" \
    --candidate "$CANDIDATE_COMMIT" --expected-base "$BASE_COMMIT" \
    > "$RUN_TMP/evidence/intra-agent-skill-update/owner-push.json"
  export PUBLISHED_COMMIT="$(jq -r '.published_commit' "$RUN_TMP/evidence/intra-agent-skill-update/owner-push.json")"
  ```

  Require `outcome=published`, `published_commit` and `effective_commit` equal to the candidate, `activation=effective`, `native_settled=true`, and `native_ready=true`.

- **Read-only cross-check.** Read the published file at the new revision and confirm the Testing line is present:

  ```bash
  python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" read \
    --run-meta "$RUN_META" --path release-notes/SKILL.md --revision "$PUBLISHED_COMMIT"
  ```

- **Verify the next load.** Send:

  ```bash
  python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" prompt \
    --run-meta "$RUN_META" --role target \
    --prompt "Use the release-notes skill to draft release notes for adding a new --verbose flag. Changed files: src/app/cli.py. Keep it short and include the Risks and Testing sections."
  ```

  In the target transcript, the `skill` tool result for `release-notes` must show a base directory ending in the published revision and instructions containing the Testing line. The final assistant output must include the Testing section.

- **Proof.** Save the target transcript, the first push receipt (published or busy), the owner push receipt, the `read` payload, the skill tool result, and `final-assistant.txt` under `$RUN_TMP/evidence/intra-agent-skill-update/`. Confirm each file exists after cleanup.

## Gotchas

- The target's native file policy is `workspace-write`; its home is outside the workspace. Direct edits to `<home>/skills` are denied. The versioned mount is the supported self-update path.
- A self-push during the agent's own active turn is refused by design; `busy` is not a transient transport error. Save the candidate, wait for idle, and publish with a fresh operation ID.
- A busy refusal preserves the candidate. Do not discard the draft or re-open a new draft at the old base.
- The mount starts empty. The first candidate creates the skill; a candidate that shadows a visible native skill is refused.
- `push-owner` assumes the target's admin roster is open. If the roster is keyed, use an enrolled admin signer instead of the owner shortcut.
- The target may be busy with an earlier prompt; `control.can_accept_prompt_now` is the readiness signal, not the gateway health alone.

## Blinding and Transcript Checks

- The prompt is an ordinary operator request. Do not include evaluation, judging, benchmark, or candidate vocabulary in prompts seen by the target.
- Grade from the target's actual tool calls, the mount revision, and the skill tool result. The agent's final summary is supporting evidence only.
- Do not keep the source role active in this case; the target is the tested agent.
