# Instructional Test Report: skill-update-run

Date: 2026-11-24 16:08 UTC | Overall Status: MIXED | Mode: run-cases

## Run Identity and Environment

- **Realwork checkout**: `/data/huangzhe/code/houmao` (branch `devel`, commit `706f9d8a6ccce10834a65a375f839d1e71e86f28`, working tree dirty: instructional bundle relocation and doc updates)
- **Enclosing metaproj**: none (standalone realwork)
- **Instructional output dir**: `/data/huangzhe/code/houmao/tests/instructional`
- **Case bundle**: `/data/huangzhe/code/houmao/tests/instructional/skill-update`
- **Project-local temp workspace**: `/data/huangzhe/code/houmao/tmp/instructional-tests/20261124T160824Z-skill-update-run`
- **Evidence root (verified post-cleanup)**: `/data/huangzhe/code/houmao/tmp/instructional-tests/20261124T160824Z-skill-update-run/evidence/` (46 files)
- **Temporary scripts used**: `scripts/env.sh` only
- **Harness and tool versions**: `houmao-mgr 3.0.0rc6+g706f9d8a`; DSH `0.2.2-rc.3`; model `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`; gateway policy `admin_mode=open`, default group `agent-requester`
- **Pair identity**: target `e4f062a5-2235-4170-be1d-f9399dcd050d` (gateway `41315`, Web origin `38881`); source `97b3131e-3f8d-419d-983f-da3f010129e5` (gateway `41893`, Web origin `34421`); mount `d2488c3fd13c41abb9e00fe2627af1ba`
- **Isolation**: each fixture prepared with `--tmux-server new`; private sockets under `/tmp/houmao-tmux-1001/8d7bee5d0672038af413d92d/`; no default tmux server or user session touched
- **Stand-in or environment deltas**: none

## Summary Table

| Bundle / Scenario | Entry Point(s) Tested | Verdict | Triage | Doctor | Surviving Evidence | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `skill-update/inter-agent-skill-update` | `houmao-mgr agents single ... files`, DSH Web agent prompts | `PASS` | `none` | `pass` | `evidence/skill-update/inter-agent-skill-update/` | Source published create `c46773ed`→`361ad4ba` and update `361ad4ba`→`086378b0`; target loaded `086378b0` with Risks. |
| `skill-update/intra-agent-skill-update` | `houmao-mgr agents self files`, owner publish | `PASS` | `none` | `pass` | `evidence/skill-update/intra-agent-skill-update/` | Self-push returned `busy/owner_maintenance_unavailable`; owner published candidate `3b0266cc`; target loaded `3b0266cc` with Testing. |
| `skill-update/missing-push-grant` | `access revoke`, source push | `FAIL` | `doc-drift` | `pass` | `evidence/skill-update/missing-push-grant/` | Revoking `files.push` did not refuse the push; open roster still admitted `reviewer` and published `08c93035`. |
| `skill-update/shadow-conflict` | source push of `houmao-agent-entrypoint` | `PASS` | `none` | `pass` | `evidence/skill-update/shadow-conflict/` | Push returned `outcome=conflict`, `reason=file_native_conflict`; published revision unchanged. |

## Per-Case Details

### `skill-update/inter-agent-skill-update` — `PASS`

- **Preconditions and Doctor**: `doctor` exited 0 with both agents available, both gateways healthy, the `skills` mount visible, and `reviewer` plus `self-editor` direct grants active. Target `e4f062a5-...`, source `97b3131e-...`.
- **Executed path**: prompted the source to create `release-notes/SKILL.md` from `$SOURCE_RUN/workdir/peer-brief.json`, then prompted it to add a Risks section. The source used its peer signer, discovered the target mount, opened a lease, wrote, committed, and pushed.
- **Expected vs. observed**: first push `outcome=published`, `published_commit=361ad4bad5ba730cb3bbb7f97b5363a3182b1b40`, base `c46773ed0c83d98abcce80947da0d6b2c3e136f5`, `publisher.kind=agent`, `publisher.principal_id=reviewer`, `activation=effective`, `native_ready=true`, `native_settled=true`. Second push published `086378b04696e872279ecc9bd7c7f72724e401f2` against base `361ad4ba...` with the same publisher and activation fields. Both prompt receipts reported `delivery_state=completed`, `success=true`.
- **Read-only cross-check**: `mounts` reported `published_commit=086378b0...`; `read` at that revision decoded to a body containing the Risks section.
- **Target load**: the target's `skill` tool result resolved `.../projection/revisions/086378b04696e872279ecc9bd7c7f72724e401f2/release-notes` and contained the Risks instruction; `final-assistant.txt` includes a Risks section.
- **Artifacts**: `create-push.json`, `update-push.json`, `mounts.json`, `read.json`, `release-notes-SKILL.md`, `target-skill-tool-result.json`, `final-assistant.txt`, `source-session.v4.jsonl`, `target-session.v4.jsonl`.
- **Triage and follow-up**: none.

### `skill-update/intra-agent-skill-update` — `PASS`

- **Preconditions and Doctor**: re-ran `doctor` after the missing-grant arm; exited 0. Target available, gateway healthy, mount visible, `self-editor` grant active.
- **Executed path**: prompted the target to add a Testing section to its own `release-notes` skill. The target used `houmao-mgr agents self files ...` to list mounts, read the published file, open a draft against base `08c93035...`, write, diff, commit, and push candidate `3b0266cce86c5c743995f93eb19617af5bd963a5`.
- **Expected vs. observed**: the self-push returned `outcome=busy`, `reason=owner_maintenance_unavailable`, with `published_commit=null`, `effective_commit=null`, `activation=not_started`, and the candidate preserved. After idle (`can_accept_prompt_now=true`), the owner publish returned `outcome=published`, `published_commit=3b0266cc...`, `effective_commit=3b0266cc...`, `activation=effective`, `native_ready=true`, `native_settled=true`.
- **Read-only cross-check**: `read` at `3b0266cc...` contains the Testing line; `mounts` reports the same published commit.
- **Target load**: the next `release-notes` load resolved `.../revisions/3b0266cce86c5c743995f93eb19617af5bd963a5/release-notes` and contained the Testing instruction; `final-assistant.txt` includes Risks, Testing, and Rollback sections.
- **Artifacts**: `push-receipt.json`, `target-idle-state.json`, `owner-push.json`, `read.json`, `release-notes-SKILL.md`, `mounts.json`, `target-skill-tool-result.json`, `final-assistant.txt`, `target-session.v4.jsonl`, `prompt-receipt.json`, `load-prompt-receipt.json`.
- **Triage and follow-up**: none for the busy path. The `--when-idle` queued variant remains unproven; the target used a plain `agents self files ... push` and the receipt was `busy`, not `queued`.

### `skill-update/missing-push-grant` — `FAIL` (`doc-drift`)

- **Preconditions and Doctor**: the pair was healthy; `access explain reviewer "files:<mount>" files.push` showed an active direct grant before revocation.
- **Executed path**: ran `access revoke reviewer "files:$MOUNT_ID" files.push`; `explain-after-revoke.json` then showed `direct_grant=null`, `admin_mode=open`, and the reviewer key still `allowed=true` with `basis=open`. Prompted the source to add a Rollback section and publish.
- **Expected vs. observed**: the case expects the push to be refused and the published revision to remain at `086378b0...`. Observed `outcome=published`, `published_commit=08c93035dc8bf0faaee6823348fb5dd4696b712f`, `publisher.principal_id=reviewer`, against base `086378b0...`. The mount advanced to `08c93035...`.
- **Read-only cross-check**: `mounts.json` confirms the advanced commit; `unexpected-push.json` confirms the publish.
- **Triage and follow-up**: `doc-drift`. The product behaves as documented in `docs/reference/gateway/operations/authorization-policy.md`: an empty admin roster runs in open mode, where every reachable key has all client-facing permissions, and direct-grant revocation does not deny access. To exercise this arm, the target must first be keyed (for example `access init --seed` or enroll an admin key) before revoking `files.push`, and the later `push-owner` step would then need an enrolled admin signer. The grant was restored after the attempt. The unexpected push added a Rollback section to the skill, which the subsequent intra case inherited.
- **Artifacts**: `revoke.json`, `explain-after-revoke.json`, `unexpected-push.json`, `mounts.json`, `prompt-receipt.json`, `source-session.v4.jsonl`, `restore.json`, `explain-after-restore.json`.

### `skill-update/shadow-conflict` — `PASS`

- **Preconditions and Doctor**: pair healthy; `reviewer` retained `files.push`.
- **Executed path**: prompted the source to create a skill named `houmao-agent-entrypoint` on the target mount.
- **Expected vs. observed**: the push returned `outcome=conflict`, `reason=file_native_conflict`, `published_commit=null`, `effective_commit=null`, `activation=not_started`, `native_ready=null`, with candidate `768d6fdd80f22b54b3a0772b5467618a3722cab8` preserved. The source retried once with a fresh operation ID and received the same `conflict`. The mount stayed at `08c93035...`.
- **Read-only cross-check**: `read` of `houmao-agent-entrypoint/SKILL.md` at the published revision failed with HTTP 404, confirming no shadowing file was published.
- **Artifacts**: `conflict-push.json`, `mounts.json`, `shadow-read.json`, `shadow-read.err`, `source-session.v4.jsonl`, `prompt-receipt.json`.
- **Triage and follow-up**: none. The case text names the arm but not the exact `conflict`/`file_native_conflict` outcome; consider documenting it during a later `audit-cases()` pass.

## Cleanup Verification

- **Stopped/removed**: `stop.json` reports both agents stopped with success (`Stopped the owned native Web Host`), and both recorded private tmux servers killed (`3924f688...sock` and `a832dfaf...sock`, status `killed`). Both socket paths are absent after cleanup.
- **Preserved**: all 46 files under `evidence/` still exist; `ps` shows no process referencing the run root. The default tmux server and user-owned sessions were not touched.
- **Residual items**: none observed.

## Unverified Scope and Next Steps

- The `--when-idle` queued self-push variant remains unproven; only the plain self-push busy refusal was exercised.
- The missing-grant arm needs a keyed target policy before it can prove a denial; the current bundle description assumes revocation denies under the default open roster.
- The shadow-conflict case should document `outcome=conflict`, `reason=file_native_conflict` as the expected refusal.
- No other bundle under `tests/instructional/` exists yet, so no other cases were skipped.
