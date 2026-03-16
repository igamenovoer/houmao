# How Do I Run A Two-Agent Mailbox Roundtrip Through CAO In A Real Project Worktree And Verify It?

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path/to/agents`).

This tutorial pack answers one concrete question:

> "How can I launch two blueprint-backed CAO sessions into a real git worktree, keep mailbox/runtime/report state under one demo-owned output directory, run `mail send -> mail check -> mail reply -> mail check`, and verify the final sanitized report against a tracked contract?"

Success means you can run the mailbox roundtrip from a clean checkout, inspect one explicit demo output directory, see both agents working inside `<demo-output-dir>/project`, and confirm the sanitized report still matches `expected_report/report.json`.

## Prerequisites Checklist

- [ ] `pixi` is installed.
- [ ] The repo environment is installed (`pixi install` once).
- [ ] `tmux` is installed and on `PATH`.
- [ ] A CAO service is reachable at `http://localhost:9889`, or you have overridden `CAO_BASE_URL`.
- [ ] The default Claude Code and Codex credential profiles selected by the tracked blueprints are available under `tests/fixtures/agents/brains/api-creds/`.
- [ ] You are running from this repository checkout.

If a prerequisite is missing or a runtime command clearly fails for credential/connectivity reasons, the wrapper exits `0` with a `SKIP:` message instead of mutating tracked files.

## Filesystem Layout

The wrapper now distinguishes the demo-owned output directory from the agent-visible workdir:

```text
<demo-output-dir>/
├── project/              # git worktree of this repository; actual agent workdir
├── runtime/              # build-brain outputs and session manifests
├── shared-mailbox/       # shared filesystem mailbox root
├── inputs/               # copied tutorial inputs
├── sender_*.json         # captured command outputs
├── receiver_*.json
├── mail_*.json
├── report.json
└── report.sanitized.json
```

By default, the wrapper uses the repo-local output directory `tmp/demo/mailbox-roundtrip-tutorial-pack`. You can override it with `--demo-output-dir <abs-or-rel-path>`. Relative paths are resolved from the repository root.

Important note: `project/` is provisioned with `git worktree add --detach ... HEAD`. That means agents see committed repository state at `HEAD`, not your uncommitted local edits in the source checkout.

## Wrapper Options

- `--demo-output-dir <path>`: select the demo-owned output directory. Relative values resolve from the repository root.
- `--jobs-dir <path>`: optional wrapper-level jobs-root override. Relative values resolve from the repository root. When omitted, Houmao keeps its default per-session job directories under `<demo-output-dir>/project/.houmao/jobs/<session-id>/`.
- `--snapshot-report`: refresh `expected_report/report.json` from the new sanitized report.

## Implementation Idea

1. Resolve one demo-owned output directory.
2. Provision `<demo-output-dir>/project` as a git worktree of the main repository.
3. Copy tracked inputs into `<demo-output-dir>/inputs`.
4. Build one Claude Code brain and one Codex brain through `build-brain --blueprint`.
5. Start both sessions through `start-session --blueprint --backend cao_rest`, using `<demo-output-dir>/project` as `--workdir`, `<demo-output-dir>/shared-mailbox` as the shared mailbox root, and optional `AGENTSYS_LOCAL_JOBS_DIR` only when `--jobs-dir` is supplied.
6. Use name-based follow-up control for `mail send`, `mail check`, `mail reply`, and `stop-session`, while preserving captured startup payloads for reporting and cleanup.
7. Build a raw report from the command artifacts, sanitize non-deterministic fields, and compare the sanitized output against `expected_report/report.json`.

The wrapper is a convenience layer. The real operator workflow is still the explicit runtime command sequence documented below.

## Critical Input Snippets

`inputs/demo_parameters.json`:

```json
{
  "schema_version": 1,
  "demo_id": "mailbox-roundtrip-tutorial-pack",
  "agent_def_dir": "tests/fixtures/agents",
  "backend": "cao_rest",
  "cao_base_url": "http://localhost:9889",
  "shared_mailbox_root_template": "{demo_output_dir}/shared-mailbox",
  "sender": {
    "blueprint": "blueprints/gpu-kernel-coder-claude.yaml",
    "agent_identity": "AGENTSYS-mailbox-sender",
    "mailbox_principal_id": "AGENTSYS-mailbox-sender",
    "mailbox_address": "AGENTSYS-mailbox-sender@agents.localhost"
  },
  "receiver": {
    "blueprint": "blueprints/gpu-kernel-coder-codex.yaml",
    "agent_identity": "AGENTSYS-mailbox-receiver",
    "mailbox_principal_id": "AGENTSYS-mailbox-receiver",
    "mailbox_address": "AGENTSYS-mailbox-receiver@agents.localhost"
  },
  "message": {
    "subject": "Mailbox tutorial roundtrip",
    "initial_body_file": "inputs/initial_message.md",
    "reply_body_file": "inputs/reply_message.md"
  }
}
```

`inputs/initial_message.md`:

```md
# Mailbox Tutorial: First Message

Please confirm that the shared mailbox is reachable from your runtime session.
```

`inputs/reply_message.md`:

```md
# Mailbox Tutorial: Reply Message

Confirmed. The mailbox roundtrip is active and this reply should stay in the same thread.
```

## Critical Example Code (Build, Start, Send, Check, Reply, Stop)

```bash
# 1) Pick one demo-owned output directory and derive the nested project workdir.
DEMO_OUTPUT_DIR="$REPO_ROOT/tmp/demo/mailbox-roundtrip-tutorial-pack"
PROJECT_DIR="$DEMO_OUTPUT_DIR/project"
RUNTIME_ROOT="$DEMO_OUTPUT_DIR/runtime"
MAILBOX_ROOT="$DEMO_OUTPUT_DIR/shared-mailbox"

# 2) Optional: relocate per-session jobs away from the project worktree.
export AGENTSYS_LOCAL_JOBS_DIR="$REPO_ROOT/tmp/demo/mailbox-jobs"

# 3) Build the sender brain from the tracked Claude blueprint.
pixi run python -m houmao.agents.realm_controller build-brain \
  --agent-def-dir tests/fixtures/agents \
  --runtime-root "$RUNTIME_ROOT" \
  --blueprint blueprints/gpu-kernel-coder-claude.yaml

# 4) Start the sender with mailbox overrides and the nested project workdir.
pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir tests/fixtures/agents \
  --runtime-root "$RUNTIME_ROOT" \
  --brain-manifest "$SENDER_MANIFEST" \
  --blueprint blueprints/gpu-kernel-coder-claude.yaml \
  --backend cao_rest \
  --cao-base-url "$CAO_BASE_URL" \
  --workdir "$PROJECT_DIR" \
  --agent-identity AGENTSYS-mailbox-sender \
  --mailbox-transport filesystem \
  --mailbox-root "$MAILBOX_ROOT" \
  --mailbox-principal-id AGENTSYS-mailbox-sender \
  --mailbox-address AGENTSYS-mailbox-sender@agents.localhost

# 5) Send the initial message from the sender to the receiver.
pixi run python -m houmao.agents.realm_controller mail send \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity AGENTSYS-mailbox-sender \
  --to AGENTSYS-mailbox-receiver@agents.localhost \
  --subject "Mailbox tutorial roundtrip" \
  --body-file "$DEMO_OUTPUT_DIR/inputs/initial_message.md"
```

Credentials still come from the blueprint-selected brain recipes. Mailbox transport, root, principal, and address stay explicit on `start-session`. The wrapper-only `--jobs-dir` flag simply maps to `AGENTSYS_LOCAL_JOBS_DIR` before the two `start-session` calls; direct `realm_controller` commands still use the env var rather than a new runtime CLI flag.

## Critical Output Snippet

Sanitized report shape:

```json
{
  "checks": {
    "receiver_start_mailbox_enabled": true,
    "receiver_stop_ok": true,
    "reply_parent_matches_send_message_id": true,
    "sender_start_mailbox_enabled": true,
    "sender_stop_ok": true,
    "shared_mailbox_root": true
  },
  "demo": "mailbox-roundtrip-tutorial-pack",
  "demo_output_dir": "<DEMO_OUTPUT_DIR>",
  "project_workdir": "<PROJECT_WORKDIR>",
  "reply_parent_message_id": "<MESSAGE_ID>"
}
```

The full tracked contract lives in `expected_report/report.json`. The placeholders above show the important masking behavior, not the complete report.

## Run + Verify Workflow

1. Run the one-click wrapper.

   ```bash
   scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh
   ```

   Or pick explicit locations:

   ```bash
   scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh \
     --demo-output-dir demos/manual-mailbox-run \
     --jobs-dir tmp/demo/mailbox-jobs
   ```

   Expected terminal lines:

   ```text
   [demo][mailbox-roundtrip] demo output dir: ...
   [demo][mailbox-roundtrip] project workdir: ...
   [demo][mailbox-roundtrip] sender_build: ok
   [demo][mailbox-roundtrip] receiver_start: ok
   verification passed
   [demo][mailbox-roundtrip] demo complete
   ```

2. Inspect the generated artifacts.

   ```bash
   ls -1 "$DEMO_OUTPUT_DIR" | rg 'sender_|receiver_|mail_|report'
   ```

   Expected key files:

   ```text
   sender_build.json
   sender_start.json
   mail_send.json
   receiver_check.json
   mail_reply.json
   sender_check.json
   sender_stop.json
   receiver_stop.json
   report.json
   report.sanitized.json
   ```

3. Compare the sanitized report manually if you want a direct diff.

   ```bash
   diff -u \
     "$DEMO_OUTPUT_DIR/report.sanitized.json" \
     scripts/demo/mailbox-roundtrip-tutorial-pack/expected_report/report.json
   ```

   Expected output:

   ```text
   # no output means the files match
   ```

## Manual Command-By-Command Walkthrough

The wrapper documents the same steps it runs:

1. Set `DEMO_OUTPUT_DIR`, provision `PROJECT_DIR="$DEMO_OUTPUT_DIR/project"` as a git worktree, and copy `inputs/` into `$DEMO_OUTPUT_DIR/inputs`.
2. Set `RUNTIME_ROOT="$DEMO_OUTPUT_DIR/runtime"` and `MAILBOX_ROOT="$DEMO_OUTPUT_DIR/shared-mailbox"`.
3. Optionally export `AGENTSYS_LOCAL_JOBS_DIR` if you want the same jobs-root override that `--jobs-dir` provides.
4. Build the Claude sender brain with `--blueprint blueprints/gpu-kernel-coder-claude.yaml`.
5. Build the Codex receiver brain with `--blueprint blueprints/gpu-kernel-coder-codex.yaml`.
6. Start both sessions with `--backend cao_rest`, `--workdir "$PROJECT_DIR"`, and explicit `--mailbox-transport`, `--mailbox-root`, `--mailbox-principal-id`, and `--mailbox-address`.
7. Save the `message_id` from `mail send`, and fail if it is blank.
8. Run receiver `mail check`, receiver `mail reply --message-id "$SEND_MESSAGE_ID"`, sender `mail check`, and then both `stop-session` calls.

Nothing in the runner depends on a tutorial-owned `state.json`. Follow-up commands target the two sessions by their name-based `--agent-identity` values, and cleanup uses the same identities if the second startup or a later command fails.

## Refresh Snapshot Contract

Use this only when mailbox behavior changes intentionally:

```bash
scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh --snapshot-report
```

Snapshot mode rewrites `expected_report/report.json` from `report.sanitized.json` only. The runner does not update tracked inputs or any other tracked files.

## Troubleshooting

- `SKIP: pixi not found on PATH`
  Install Pixi and retry.
- `SKIP: tmux not found on PATH`
  Install tmux and retry because CAO-backed sessions still depend on tmux-managed runtime recovery.
- `SKIP: missing credentials`
  Create the credential env files referenced by the tracked Claude and Codex recipes under `tests/fixtures/agents/brains/api-creds/`.
- `SKIP: connectivity unavailable`
  Start or repair the CAO service at `CAO_BASE_URL`, then retry.
- `FAIL: demo project directory exists but is not a git worktree of the repository`
  Remove or relocate the incompatible `<demo-output-dir>/project` directory, then rerun.
- `FAIL: command failed during receiver_start`
  Inspect `receiver_start.err`. The wrapper should still stop the already-started sender during trap cleanup.
- `sanitized report mismatch`
  Re-run in snapshot mode if the behavior change is intentional; otherwise inspect the raw report and the captured per-step JSON outputs for regressions.

## Appendix: Key Parameters

| Name | Value | Explanation |
|---|---|---|
| `backend` | `cao_rest` | Forces the tutorial through the CAO-backed runtime path. |
| Sender blueprint | `blueprints/gpu-kernel-coder-claude.yaml` | Selects the default Claude Code recipe and `gpu-kernel-coder` role. |
| Receiver blueprint | `blueprints/gpu-kernel-coder-codex.yaml` | Selects the default Codex recipe and `gpu-kernel-coder` role. |
| `--demo-output-dir` | `tmp/demo/mailbox-roundtrip-tutorial-pack` by default | Demo-owned output root for the nested project worktree, mailbox root, runtime root, copied inputs, and reports. |
| Agent workdir | `<demo-output-dir>/project` | Git worktree used as the actual `start-session --workdir` for both agents. |
| `shared_mailbox_root_template` | `{demo_output_dir}/shared-mailbox` | Keeps the mailbox root shared inside the selected demo output directory. |
| `--jobs-dir` | optional wrapper override | Redirects per-session job dirs through `AGENTSYS_LOCAL_JOBS_DIR`; omit it to keep Houmao's default under `<demo-output-dir>/project/.houmao/jobs/<session-id>/`. |
| Sender identity | `AGENTSYS-mailbox-sender` | Name-based recovery target used for send, check, and stop. |
| Receiver identity | `AGENTSYS-mailbox-receiver` | Name-based recovery target used for check, reply, and stop. |
| `CAO_BASE_URL` | `http://localhost:9889` by default | Override when your CAO service is reachable on a different loopback endpoint. |
| `CAO_PROFILE_STORE` | optional env override | Pass this when you need a non-default CAO profile-store directory. |

## Appendix: File Inventory

Tracked inputs:

- `inputs/demo_parameters.json`
- `inputs/initial_message.md`
- `inputs/reply_message.md`

Tracked expected output:

- `expected_report/report.json`

Scripts:

- `run_demo.sh`
- `scripts/tutorial_pack_helpers.py`
- `scripts/sanitize_report.py`
- `scripts/verify_report.py`

Generated demo-output-dir artifacts:

- `project/`
- `runtime/`
- `shared-mailbox/`
- `inputs/`
- `sender_build.json`, `sender_build.err`
- `receiver_build.json`, `receiver_build.err`
- `sender_start.json`, `sender_start.err`
- `receiver_start.json`, `receiver_start.err`
- `mail_send.json`, `mail_send.err`
- `receiver_check.json`, `receiver_check.err`
- `mail_reply.json`, `mail_reply.err`
- `sender_check.json`, `sender_check.err`
- `sender_stop.json`, `sender_stop.err`
- `receiver_stop.json`, `receiver_stop.err`
- `report.json`
- `report.sanitized.json`
- `cleanup_sender_stop.json` / `cleanup_receiver_stop.json` only when trap cleanup had to intervene
