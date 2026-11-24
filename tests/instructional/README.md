# Instructional Skill-Update Suite

Agent-driven verification for intra-agent and inter-agent updates of a managed DSH Web agent's versioned `skills` mount. The suite exercises the real managed-agent surface: `houmao-mgr agents single ... files` discovery, draft leases, commits, publication receipts, target skill loading, and the documented busy refusal for a self-push during the agent's own active turn.

## Baseline Preconditions & Isolation

- Realwork checkout: `/data/huangzhe/code/houmao` on `devel`.
- Manager: the uv-installed `houmao-mgr` 3.0.0rc6 or newer. Set `HOUMAO_MGR` to that binary. The current dev box uses `/home/huangzhe/.local/share/uv/tools/houmao/bin/houmao-mgr`.
- Model lane: self-hosted Qwen at `http://127.0.0.1:14888/v1`, model `Qwen/Qwen3.8-27B-FP8`, context window `262144`, maximum output tokens `8192`, reasoning map `{"low":"low","medium":"medium","off":"none","xhigh":"xhigh"}`, compatibility `{"supports_developer_role":false}`.
- DSH executable: the qualified build `0.2.2-rc.3` at `/data/huangzhe/code/houmao/tmp/dsh/npm-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js`.
- Project-local temporary root: `<repo>/tmp/instructional-tests/<run-id>/`. `tmp/` is Git-ignored; every script, disposable runtime directory, and proof artifact stays there.
- Isolation: each fixture prepares with `--tmux-server new` and owns a separate tmux socket, registry, runtime root, home, gateway port, and native Web origin. Never touch the caller's default tmux server, the R13 campaign pair, or any agent this run did not create.
- Target launch posture: `managed_web_skills: true` in the DSH tool params, prompt mode `as_is`, native permission parameters at their defaults, DSH Web backend, attached gateway.
- Concurrency: a target accepts one active prompt at a time. The source and target may run side by side; do not double-drive the same target.

## Launch

Set the shared shell variables first. These are concrete values, not prompts for user input.

```bash
export REPO_ROOT="/data/huangzhe/code/houmao"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-skill-update"
export RUN_TMP="$REPO_ROOT/tmp/instructional-tests/$RUN_ID"
export HOUMAO_MGR="${HOUMAO_MGR:-/home/huangzhe/.local/share/uv/tools/houmao/bin/houmao-mgr}"
export DSH_EXECUTABLE="${DSH_EXECUTABLE:-$REPO_ROOT/tmp/dsh/npm-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js}"
export BASE_URL="http://127.0.0.1:14888/v1"
export MODEL="Qwen/Qwen3.8-27B-FP8"
mkdir -p "$RUN_TMP/runtime/runs" "$RUN_TMP/runtime/runs-source" "$RUN_TMP/evidence"
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
  --system-prompt-file "$REPO_ROOT/tests/instructional/helpers/roles/skill-target.md" \
  --run-root "$RUN_TMP/runtime/runs" > "$RUN_TMP/evidence/target-prepare.json"
export TARGET_RUN="$(jq -r '.run_dir' "$RUN_TMP/evidence/target-prepare.json")"
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
  --system-prompt-file "$REPO_ROOT/tests/instructional/helpers/roles/skill-source.md" \
  --run-root "$RUN_TMP/runtime/runs-source" > "$RUN_TMP/evidence/source-prepare.json"
export SOURCE_RUN="$(jq -r '.run_dir' "$RUN_TMP/evidence/source-prepare.json")"
test -f "$SOURCE_RUN/run.json"
```

Enable the mount on the prepared target, then launch both agents. `enable-mount` refuses an already-launched run because the DSH mount is a launch-time provider.

```bash
python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" \
  enable-mount --run-dir "$TARGET_RUN" > "$RUN_TMP/evidence/enable-mount.json"

pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" \
  launch --run-dir "$TARGET_RUN" > "$RUN_TMP/evidence/target-launch.json"
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" \
  launch --run-dir "$SOURCE_RUN" > "$RUN_TMP/evidence/source-launch.json"
```

Configure the pair. The helper writes two Ed25519 peer signers under `$RUN_TMP/runtime/keys/`, enrolls `reviewer` (the source) and `self-editor` (the target) on the target, grants `files.read`, `files.edit`, and `files.push` on the exact `skills` mount, writes the source's `peer-brief.json`, and writes the run handle.

```bash
python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" configure \
  --target-run "$TARGET_RUN" --source-run "$SOURCE_RUN" \
  --run-meta "$RUN_TMP/run-meta.json" --evidence-root "$RUN_TMP/evidence" \
  > "$RUN_TMP/evidence/configure.json"
export RUN_META="$RUN_TMP/run-meta.json"
```

## Doctor

```bash
python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" doctor --run-meta "$RUN_META"
```

Doctor exits zero only when both agents are available, both gateways are healthy, the target exposes a `skills` mount, and both retained principals have an active `files.push` direct grant. The `access explain` key check can report `allowed: null` because the live plugin catalog is unresolved; the retained direct grant being active is the required evidence.

## Drive

Use the helper so the exact run roots and tmux-clearing environment are selected. Each prompt is a normal operator request; do not include evaluation vocabulary in prompts seen by the agents.

Resolve the run handles once. Every case command uses these variables rather than re-deriving IDs by hand.

```bash
export TARGET_RUN="$(jq -r '.target_run' "$RUN_META")"
export SOURCE_RUN="$(jq -r '.source_run' "$RUN_META")"
export TARGET_AGENT="$(jq -r '.target_agent_id' "$RUN_META")"
export SOURCE_AGENT="$(jq -r '.source_agent_id' "$RUN_META")"
export MOUNT_ID="$(jq -r '.mount_id' "$RUN_META")"
```

```bash
python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" prompt \
  --run-meta "$RUN_META" --role source \
  --prompt "Read the peer brief at $SOURCE_RUN/workdir/peer-brief.json. Update the target agent's release-notes skill so it also includes a short 'Risks' section after the verification note. Use your configured peer signer, discover the target mount, publish one candidate, and report the push receipt."
```

Read-only cross-checks use `mounts` and `read`; an owner recovery publish uses `push-owner`.

```bash
python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" mounts --run-meta "$RUN_META"
python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" read \
  --run-meta "$RUN_META" --path release-notes/SKILL.md --revision "$PUBLISHED_COMMIT"
python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" push-owner \
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

Save every artifact under `$RUN_TMP/evidence/<case-slug>/`.

| Artifact | Required evidence |
| --- | --- |
| `source-session.v4.jsonl` or the selected tool-call lines | The source's `files mounts`, `lease open`, `write`, `commit`, and `push` calls with the exact target coordinates and `--self-signer`. |
| `push.json` / `push-receipt.json` | `outcome`, `publisher`, `published_commit`, `effective_commit`, `activation`, `native_settled`, and `native_ready` kept separate. |
| `mounts.json` / `read.json` | The published revision and the changed file content read from the target mount. |
| `target-skill-tool-result.json` | The target's `skill` tool result showing the new revision path and the new instruction body. |
| `final-assistant.txt` | The target's user-visible output includes the new section. |
| `busy-receipt.json` (intra case) | `outcome=busy`, `reason=owner_maintenance_unavailable`, candidate saved, no published/effective commit. |
| `owner-push.json` (intra case) | The saved candidate published after the target became idle, with `activation=effective` and `native_ready=true`. |

A pass requires the triggering action and the resulting state from two views: the agent transcript or command receipt, plus a read-only mount read or target skill load. Cleanup must preserve `evidence/`.

## Cleanup

```bash
python3 "$REPO_ROOT/tests/instructional/helpers/skill_update_lab.py" stop --run-meta "$RUN_META"
```

`stop` stops only the two agents recorded in the run handle, kills only the recorded private tmux servers, removes only their stale sockets, and leaves `evidence/` untouched. It is idempotent for an already-stopped pair. If a stop fails for any other reason, report the exact error; do not kill processes by name or touch the default tmux server.

## Helpers

| Helper | Invocation | Purpose |
| --- | --- | --- |
| `helpers/skill_update_lab.py` | `python3 helpers/skill_update_lab.py <subcommand> --help` | Prepare, configure, doctor, drive, and stop the pair. |
| `helpers/roles/skill-target.md` | `fixture.py prepare --role skill-target --system-prompt-file ...` | General target-agent role; not a narrow smoke-test role. |
| `helpers/roles/skill-source.md` | `fixture.py prepare --role skill-source --system-prompt-file ...` | General source-agent role for peer updates. |

`skill_update_lab.py` subcommands are `enable-mount`, `configure`, `doctor`, `prompt`, `state`, `mounts`, `read`, `push-owner`, and `stop`. It defaults to `$HOUMAO_MGR`, then `houmao-mgr` on `PATH`, then the uv tool path.

## Case Index

| Case | Capability tags | User-visible behavior |
| --- | --- | --- |
| [intra-agent-skill-update.md](cases/intra-agent-skill-update.md) | `multi-agent`, `dsh-web`, `versioned-files`, `guardrail` | The agent updates its own published skill through its authorized mount, survives the documented self-push busy refusal, and loads the new body on the next turn. |
| [inter-agent-skill-update.md](cases/inter-agent-skill-update.md) | `multi-agent`, `dsh-web`, `versioned-files`, `peer-auth` | An authorized source agent publishes a skill change on a target agent's mount, and the target loads the new revision on its next turn. |

## Last Self-Proof

Run on 2026-11-24 with `houmao-mgr 3.0.0rc6+gf7560227` at repo `f7560227`.

- Helper-driven inter-agent proof: `tmp/instructional-tests/20261124-skill-update-helper-selftest/` followed the README Launch, Doctor, Drive, Evidence, and Cleanup path. `doctor` exited zero with both agents available, both gateways healthy, the `skills` mount visible, and both grants active. Source agent `a71eaaea-f7d9-4d79-a507-3a909d63ac06` created commit `6d3d90ef366fc8f6912bcdf33ba63221e666cf8a` and updated it to `3cb3561f9540882753e2f49dac824858cd99675e` on target `4f7ebe2d-9115-48d7-940d-257052621b88`; both receipts reported `outcome=published`, `publisher.kind=agent`, `principal_id=reviewer`, `activation=effective`, and `native_ready=true`. The target's next skill load resolved `3cb3561f9540882753e2f49dac824858cd99675e` and its output included the Risks section. `stop` reported both agents stopped, killed only the two recorded private tmux servers, and the evidence files survived.
- Manual intra-agent and inter-agent proof: `tmp/instructional-tests/20261124-skill-update-selftest/` exercised the same commands directly. The source agent `56174971-5489-442b-8f99-9fa19a4885b9` published `release-notes` on target `cc111834-cfac-417f-8661-320b2976fe5d` at `5ce7e8ffdf9592f7feb2d6f000842c4b2e4b8e17`; the target loaded that revision. The target then drafted `f3b12778132db169bd3f06a8c916c11f1afed60a` and its self-push returned `outcome=busy` with `reason=owner_maintenance_unavailable`; the owner published the saved candidate after the turn, and the target's next load resolved that revision and included the Testing section.
- Surviving evidence: `tmp/instructional-tests/20261124-skill-update-helper-selftest/evidence/inter-agent-skill-update/`, `tmp/instructional-tests/20261124-skill-update-selftest/evidence/inter-agent-publish/`, and `tmp/instructional-tests/20261124-skill-update-selftest/evidence/intra-agent-publish/`. These files are disposable but were verified after cleanup.

The guardrail sub-cases for a revoked `files.push`, a shadowed native skill, and a stale base are documented in the case files but were not all exercised in this self-proof. Verify their exact refusal outcomes before treating them as proven.
