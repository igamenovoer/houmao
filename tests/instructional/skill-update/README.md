# Instructional Skill-Update Suite

Agent-driven verification for intra-agent and inter-agent updates of a managed DSH Web agent's versioned `skills` mount. The suite exercises the real managed-agent surface: `houmao-mgr agents single ... files` discovery, draft leases, commits, publication receipts, target skill loading, and the documented busy refusal for a self-push during the agent's own active turn.

## Baseline Preconditions & Isolation

- Realwork checkout: Houmao repository root on `devel` (`$REPO_ROOT`, resolved via `git rev-parse --show-toplevel`).
- Manager: the uv-installed `houmao-mgr` 3.0.0rc6 or newer. Set `HOUMAO_MGR` to that binary (defaulting to `houmao-mgr` on `PATH` or `$HOME/.local/share/uv/tools/houmao/bin/houmao-mgr`).
- Model lane: self-hosted Qwen at `http://127.0.0.1:14888/v1`, model `Qwen/Qwen3.8-27B-FP8`, context window `262144`, maximum output tokens `8192`, reasoning map `{"low":"low","medium":"medium","off":"none","xhigh":"xhigh"}`, compatibility `{"supports_developer_role":false}`.
- DSH executable: the qualified build `0.2.2-rc.3` at `$REPO_ROOT/tmp/dsh/npm-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js`.
- Project-local temporary root: `$REPO_ROOT/tmp/instructional-tests/<run-id>/`. `tmp/` is Git-ignored; every temporary script (`scripts/`), disposable runtime directory (`runtime/`), and surviving proof artifact (`evidence/skill-update/<scenario-slug>/`) stays there.
- Isolation: each fixture prepares with `--tmux-server new` and owns a separate tmux socket, registry, runtime root, home, gateway port, and native Web origin. Never touch the caller's default tmux server or any agent this run did not create.
- Target launch posture: `managed_web_skills: true` in the DSH tool params, prompt mode `as_is`, native permission parameters at their defaults, DSH Web backend, attached gateway.
- Admin roster: a fresh target starts with an empty roster and runs in `admin_mode=open`. The missing-push-grant arm closes it with `key-admin` before revoking; run that arm after the intra-agent case.
- Concurrency: a target accepts one active prompt at a time. The source and target may run side by side; do not double-drive the same target.

## Launch

Set the shared shell variables first. These are concrete values, not prompts for user input.

```bash
export REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"
export BUNDLE_ROOT="$REPO_ROOT/tests/instructional/skill-update"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-skill-update"
export RUN_TMP="$REPO_ROOT/tmp/instructional-tests/$RUN_ID"
export HOUMAO_MGR="${HOUMAO_MGR:-$(command -v houmao-mgr || echo "$HOME/.local/share/uv/tools/houmao/bin/houmao-mgr")}"
export DSH_EXECUTABLE="${DSH_EXECUTABLE:-$REPO_ROOT/tmp/dsh/npm-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js}"
export BASE_URL="http://127.0.0.1:14888/v1"
export MODEL="Qwen/Qwen3.8-27B-FP8"
mkdir -p "$RUN_TMP/scripts" "$RUN_TMP/runtime/runs" "$RUN_TMP/runtime/runs-source" "$RUN_TMP/evidence/skill-update"
git check-ignore -q "$RUN_TMP" || { echo "RUN_TMP is not Git-ignored: $RUN_TMP" >&2; exit 1; }
curl -fsS "$BASE_URL/models" >/dev/null
test -x "$DSH_EXECUTABLE"
```

Prepare the target from the tracked target role. The `skills` mount is exposed only when the target launches with `managed_web_skills: true`.

```bash
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" prepare \
  --case self-hosted --client dsh --mode web --surface manager \
  --model "$MODEL" --base-url "$BASE_URL" \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"low":"low","medium":"medium","off":"none","xhigh":"xhigh"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --executable "$DSH_EXECUTABLE" --prompt-mode as_is --tmux-server new \
  --role skill-target \
  --system-prompt-file "$BUNDLE_ROOT/helpers/roles/skill-target.md" \
  --run-root "$RUN_TMP/runtime/runs" > "$RUN_TMP/evidence/skill-update/target-prepare.json"
export TARGET_RUN="$(jq -r '.run_dir' "$RUN_TMP/evidence/skill-update/target-prepare.json")"
test -f "$TARGET_RUN/run.json"
```

Prepare the source from the tracked source role. The source does not need the mount; it needs its own gateway and peer signer.

```bash
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" prepare \
  --case self-hosted --client dsh --mode web --surface manager \
  --model "$MODEL" --base-url "$BASE_URL" \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"low":"low","medium":"medium","off":"none","xhigh":"xhigh"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --executable "$DSH_EXECUTABLE" --prompt-mode as_is --tmux-server new \
  --role skill-source \
  --system-prompt-file "$BUNDLE_ROOT/helpers/roles/skill-source.md" \
  --run-root "$RUN_TMP/runtime/runs-source" > "$RUN_TMP/evidence/skill-update/source-prepare.json"
export SOURCE_RUN="$(jq -r '.run_dir' "$RUN_TMP/evidence/skill-update/source-prepare.json")"
test -f "$SOURCE_RUN/run.json"
```

Enable the mount on the prepared target, then launch both agents. `enable-mount` refuses an already-launched run because the DSH mount is a launch-time provider.

```bash
python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" \
  enable-mount --run-dir "$TARGET_RUN" > "$RUN_TMP/evidence/skill-update/enable-mount.json"

pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" \
  launch --run-dir "$TARGET_RUN" > "$RUN_TMP/evidence/skill-update/target-launch.json"
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" \
  launch --run-dir "$SOURCE_RUN" > "$RUN_TMP/evidence/skill-update/source-launch.json"
```

Configure the pair. The helper writes two Ed25519 peer signers under `$RUN_TMP/runtime/keys/`, enrolls `reviewer` (the source) and `self-editor` (the target) on the target, grants `files.read`, `files.edit`, and `files.push` on the exact `skills` mount, writes the source's `peer-brief.json`, and writes the run handle.

```bash
python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" configure \
  --target-run "$TARGET_RUN" --source-run "$SOURCE_RUN" \
  --run-meta "$RUN_TMP/run-meta.json" --evidence-root "$RUN_TMP/evidence/skill-update" \
  > "$RUN_TMP/evidence/skill-update/configure.json"
export RUN_META="$RUN_TMP/run-meta.json"
```

## Doctor

```bash
python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" doctor --run-meta "$RUN_META"
```

Doctor exits zero only when both agents are available, both gateways are healthy, the target exposes a `skills` mount, and both retained principals have an active `files.push` direct grant. The `access explain` key check can report `allowed: null` because the live plugin catalog is unresolved; the retained direct grant being active is the required evidence. Run `doctor` before the missing-grant arm. Once the roster is keyed, mount discovery needs a signer and the reviewer `files.push` check fails by design after the revoke; use `access explain` and `mounts --signer` during the arm instead.

## Drive

Use the helper so the exact run roots and tmux-clearing environment are selected. Each prompt is a normal operator request; do not include evaluation vocabulary in prompts seen by the agents.

Recommended order: inter-agent create/update/load, intra-agent self-update, keyed missing-grant arm, shadow conflict. The keyed arm changes owner-publish requirements, so keep it after the cases that use the open-roster shortcut.

Resolve the run handles once. Every case command uses these variables rather than re-deriving IDs by hand.

```bash
export TARGET_RUN="$(jq -r '.target_run' "$RUN_META")"
export SOURCE_RUN="$(jq -r '.source_run' "$RUN_META")"
export TARGET_AGENT="$(jq -r '.target_agent_id' "$RUN_META")"
export SOURCE_AGENT="$(jq -r '.source_agent_id' "$RUN_META")"
export MOUNT_ID="$(jq -r '.mount_id' "$RUN_META")"
```

```bash
python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" prompt \
  --run-meta "$RUN_META" --role source \
  --prompt "Read the peer brief at $SOURCE_RUN/workdir/peer-brief.json. Update the target agent's release-notes skill so it also includes a short 'Risks' section after the verification note. Use your configured peer signer, discover the target mount, publish one candidate, and report the push receipt."
```

Read-only cross-checks use `mounts` and `read`; an owner recovery publish uses `push-owner`.

```bash
python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" mounts --run-meta "$RUN_META"
python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" read \
  --run-meta "$RUN_META" --path release-notes/SKILL.md --revision "$PUBLISHED_COMMIT"
python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" push-owner \
  --run-meta "$RUN_META" --candidate "$CANDIDATE_COMMIT" --expected-base "$BASE_COMMIT"
```

Agent transcripts are the primary proof for agent behavior. Locate the target and source session files with the run directories recorded in `$RUN_META`.

```bash
jq -r '.target_run, .source_run' "$RUN_META"
find "$TARGET_RUN/runtime/homes" -path '*/sessions/*/session.v4.jsonl' -type f
find "$SOURCE_RUN/runtime/homes" -path '*/sessions/*/session.v4.jsonl' -type f
```

Grade from the tested agent's transcript, tool calls, and durable mount state; the agent's final summary is supporting evidence, not proof.

## Evidence

Save every artifact under `$RUN_TMP/evidence/skill-update/<scenario-slug>/`.

| Artifact | Required evidence |
| --- | --- |
| `source-session.v4.jsonl` or the selected tool-call lines | The source's `files mounts`, `lease open`, `write`, `commit`, and `push` calls with the exact target coordinates and `--self-signer`. |
| `push.json` / `push-receipt.json` | `outcome`, `publisher`, `published_commit`, `effective_commit`, `activation`, `native_settled`, and `native_ready` kept separate. |
| `mounts.json` / `read.json` | The published revision and the changed file content read from the target mount. |
| `target-skill-tool-result.json` | The target's `skill` tool result showing the new revision path and the new instruction body. |
| `final-assistant.txt` | The target's user-visible output includes the new section. |
| `busy-receipt.json` (intra case) | `outcome=busy`, `reason=owner_maintenance_unavailable`, candidate saved, no published/effective commit. |
| `owner-push.json` (intra case) | The saved candidate published after the target became idle, with `activation=effective` and `native_ready=true`. |
| `key-admin.json` (missing-grant arm) | `admin_mode=keyed`, the generated admin key path, and the reviewer direct grant still active. |
| `deny-explain.json` (missing-grant arm) | `admin_mode=keyed`, `direct_grant=null`, and a non-allowed `files.push` decision after the revoke. |
| `mounts-after-denial.json` (missing-grant arm) | Mounts read with the admin signer, proving `published_commit` is unchanged after the refused push. |
| `denied-push.json` or raw denial (missing-grant arm) | The refusal output, an unchanged `published_commit`/mount revision, and the preserved candidate commit. |
| `candidate-history.json` (missing-grant arm) | The retained candidate commit with `parent` equal to the pre-revoke published revision. |

A pass requires the triggering action and the resulting state from two views: the agent transcript or command receipt, plus a read-only mount read or target skill load. Cleanup must preserve `evidence/`.

## Cleanup

```bash
python3 "$BUNDLE_ROOT/helpers/skill_update_lab.py" stop --run-meta "$RUN_META"
```

`stop` stops only the two agents recorded in the run handle, kills only the recorded private tmux servers, removes only their stale sockets, and leaves `evidence/` untouched. It is idempotent for an already-stopped pair. If a stop fails for any other reason, report the exact error; do not kill processes by name or touch the default tmux server.

## Helpers

| Helper | Invocation | Purpose |
| --- | --- | --- |
| `helpers/skill_update_lab.py` | `python3 tests/instructional/skill-update/helpers/skill_update_lab.py <subcommand> --help` | Prepare, configure, key the target roster, doctor, drive, and stop the pair. |
| `helpers/roles/skill-target.md` | `fixture.py prepare --role skill-target --system-prompt-file tests/instructional/skill-update/helpers/roles/skill-target.md` | General target-agent role; not a narrow smoke-test role. |
| `helpers/roles/skill-source.md` | `fixture.py prepare --role skill-source --system-prompt-file tests/instructional/skill-update/helpers/roles/skill-source.md` | General source-agent role for peer updates. |

`skill_update_lab.py` subcommands are `enable-mount`, `configure`, `key-admin`, `doctor`, `prompt`, `state`, `mounts`, `read`, `push-owner`, `extract-push`, and `stop`. `key-admin` creates `$RUN_TMP/runtime/keys/target-admin`, enrolls it with `access admin-add --first`, and verifies `admin_mode=keyed`. `mounts`, `read`, and `push-owner` accept `--signer` for a keyed roster; omit it while the roster is open. It defaults to `$HOUMAO_MGR`, then `houmao-mgr` on `PATH`, then the uv tool path.

## Case Index

| Case | Capability tags | User-visible behavior |
| --- | --- | --- |
| [intra-agent-skill-update.md](cases/intra-agent-skill-update.md) | `multi-agent`, `dsh-web`, `versioned-files`, `guardrail` | The agent updates its own published skill through its authorized mount, survives the documented self-push busy refusal, and loads the new body on the next turn. |
| [inter-agent-skill-update.md](cases/inter-agent-skill-update.md) | `multi-agent`, `dsh-web`, `versioned-files`, `peer-auth` | An authorized source agent publishes a skill change on a target agent's mount, and the target loads the new revision on its next turn; the guardrail arm keys the roster before revoking `files.push`. |

## Last Self-Proof

Run on 2026-11-24 with `houmao-mgr 3.0.0rc6+g706f9d8a` at repo `706f9d8a` after reorganizing the bundle under `tests/instructional/skill-update/` and adding `extract-push`:

- Bundle-layout inter-agent proof: `tmp/instructional-tests/20261124T155733Z-skill-update-reproof/` followed the `tests/instructional/skill-update/README.md` Launch, Doctor, Drive, Evidence, and Cleanup path. `doctor` exited zero with both agents available, both gateways healthy, the `skills` mount (`aec6ad929ef14ede8b42c93be81921b9`) visible, and both grants active. Source agent `df3a9f3d-5cb4-4250-8980-63ccce0f0692` created commit `561ee39e891cea139a171bcd8849359fe9f49a99` and updated it to `fb8aafa60ef2b6d2b056e9cbc66c6fc28a87b477` on target `32c07896-23b7-49d9-b00f-dd6f37a0ec7a`; both `extract-push` receipts reported `outcome=published`, `publisher.kind=agent`, `principal_id=reviewer`, `activation=effective`, and `native_ready=true`. `mounts` and `read` confirmed revision `fb8aafa60ef2b6d2b056e9cbc66c6fc28a87b477` with the Risks section, and the target's next `release-notes` skill load resolved `.../projection/revisions/fb8aafa60ef2b6d2b056e9cbc66c6fc28a87b477/release-notes` and emitted the Risks section. `stop` reported both agents stopped, killed only the two recorded private tmux servers, and all artifacts under `evidence/skill-update/` survived cleanup.
- Prior intra-agent and inter-agent proof (`f7560227`, 2026-11-24): `tmp/instructional-tests/20261124-skill-update-selftest/` also exercised the intra-agent path where the target drafted `f3b12778132db169bd3f06a8c916c11f1afed60a`, its self-push returned `outcome=busy` with `reason=owner_maintenance_unavailable`, the owner published the saved candidate after the turn, and the target's next load resolved that revision with the Testing section.
- Full bundle live pass (`20261124T160824Z-skill-update-run`): inter-agent create/update/load passed (`c46773ed`→`361ad4ba`→`086378b0`), the intra-agent busy path passed (`3b0266cc` published by the owner and loaded on the next turn), and the shadow-conflict arm passed with `outcome=conflict` and `reason=file_native_conflict`. The missing-grant arm failed because the target was still `admin_mode=open`, which prompted the keyed revision in this bundle.
- Keyed missing-grant proof (`20261124T162844Z-skill-update-keyed-proof`): `key-admin` enrolled `target-admin` and reported `admin_mode=keyed`; revoking `files.push` changed `access explain` to `allowed: false` with `reason=insufficient_authority`. The source's push of candidate `20b87aa17a4c152c8bfad725771f42b340dcfba6` against base `429d78873a934204bfc7c3a0aeb4ad72f7573f27` returned `HTTP 403`; `mounts --signer` kept `published_commit=429d7887...`, and `history --candidates` retained the candidate with that parent. The grant was restored (`allowed: true`, `basis: scoped`) and the pair stopped cleanly.
- Surviving evidence: `tmp/instructional-tests/20261124T155733Z-skill-update-reproof/evidence/skill-update/inter-agent-skill-update/`, `tmp/instructional-tests/20261124T160824Z-skill-update-run/evidence/skill-update/`, and `tmp/instructional-tests/20261124T162844Z-skill-update-keyed-proof/evidence/skill-update/` (disposable and verified present after cleanup).

The `--when-idle` queued self-push option remains unproven on `706f9d8a`. The intra busy path, the keyed `files.push` revocation, and the shadow conflict have been re-executed live.
