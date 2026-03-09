# Issue: `cao-interactive-full-pipeline-demo` Default Run Requires Workarounds

## Summary

On 2026-03-09, trying to run `scripts/demo/cao-interactive-full-pipeline-demo` directly from this repository did not work end to end with the default wrapper behavior. I hit a startup failure caused by a CAO working-directory policy mismatch, then a server reuse problem, then a session-lifecycle problem when invoking the wrappers as one-shot commands from separate non-interactive shells. I was able to complete the demo with an operational workaround, but the default path is still fragile and should be treated as a known issue.

## What Failed

### 1. Default `launch_alice.sh` failed during `start-session`

The first launch attempt failed with:

```text
Working directory not allowed: /data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents ... which is outside home directory /data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/tmp/cao_interactive_full_pipeline_demo
```

Captured in:

- `tmp/cao_interactive_full_pipeline_demo/logs/start-session.stderr`

This happened because:

- `run_demo.sh` defaults `CAO_LAUNCHER_HOME_DIR` to the demo workspace root.
- `run_demo.sh` also passes `--workdir "$REPO_ROOT"` to the runtime.
- The CAO server rejected the repo root because it was outside the configured launcher home.

### 2. Changing `CAO_LAUNCHER_HOME_DIR` alone was not enough

After setting `CAO_LAUNCHER_HOME_DIR="$PWD"`, the launch still failed with the same error. The generated launcher config was correct, but the CAO launcher reported:

```json
{
  "message": "CAO server already healthy at http://127.0.0.1:9889.",
  "reused_existing_process": true
}
```

The existing server on fixed port `127.0.0.1:9889` was reused with the old home-directory policy still active, so the new config never took effect.

### 3. Non-interactive wrapper calls were not stable for the full flow

After explicitly stopping the old CAO server and relaunching with `CAO_LAUNCHER_HOME_DIR="$PWD"`, `launch_alice.sh` succeeded, but the next `send_prompt.sh` failed with:

```text
Failed to fetch CAO terminal output (terminal_id=15344c9d, mode=full): [Errno 111] Connection refused
```

At that point the session manifest existed, but the CAO server was no longer reachable. In this environment, invoking the wrapper scripts as separate one-shot commands was not reliable for keeping the launcher-managed server alive long enough to complete the interactive workflow.

### 4. A stale tmux session blocked a later restart

When I retried inside a persistent shell with a fresh workspace, startup initially failed with:

```text
Explicit agent identity `AGENTSYS-alice` is already in use by an existing tmux session.
```

That stale tmux session came from the earlier partial launch and had to be stopped before the clean retry could succeed.

## How I Solved It

I was able to complete the demo successfully with this sequence:

1. Use a persistent interactive shell instead of separate one-shot command invocations.
2. Export `CAO_LAUNCHER_HOME_DIR="$PWD"` so the repo root workdir is inside the CAO home policy.
3. Use a fresh workspace, for example `DEMO_WORKSPACE_ROOT="$PWD/tmp/cao_interactive_full_pipeline_demo_tty"`.
4. Stop any previous launcher-managed CAO server on `127.0.0.1:9889` so the new launcher config actually takes effect.
5. Stop any stale `AGENTSYS-alice` session before relaunching.
6. Run the full flow from the same persistent shell:
   - `scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh`
   - `scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh --prompt "...first prompt..."`
   - `scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh --prompt "...second prompt..."`
   - `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh verify`
   - `scripts/demo/cao-interactive-full-pipeline-demo/stop_demo.sh`
7. Stop the launcher-managed CAO server after the run to avoid leaving the fixed-port service behind.

## Successful Run Evidence

Using the workaround above, I completed the demo in:

- `tmp/cao_interactive_full_pipeline_demo_tty/`

Notable artifacts:

- `tmp/cao_interactive_full_pipeline_demo_tty/state.json`
- `tmp/cao_interactive_full_pipeline_demo_tty/report.json`
- `tmp/cao_interactive_full_pipeline_demo_tty/turns/turn-001.json`
- `tmp/cao_interactive_full_pipeline_demo_tty/turns/turn-002.json`

`run_demo.sh verify` passed against that workspace.

## Remaining Gaps

The issue is not fully fixed in code yet. The current demo still depends on operator knowledge that is not encoded in the default wrappers:

- launcher home must include the repo workdir, or startup fails
- fixed-port CAO server reuse can preserve stale policy from an older config
- separate non-interactive wrapper invocations may not preserve the CAO server lifecycle reliably in this environment

There was also one odd runtime observation during the successful run: the second prompt's extracted `response_text` repeated the first-turn confirmation, but `verify` still passed because the verifier only checks for two non-empty successful turns with one reused agent identity.

## Suggested Follow-Up

- Make the demo's default launcher home and default workdir compatible without requiring manual env overrides.
- Handle stale fixed-port server reuse more aggressively when the launcher config changes.
- Decide whether the demo should explicitly manage CAO server lifecycle across separate wrapper invocations, or clearly document that the main walkthrough must run from one persistent shell.
- Tighten verification if prompt-to-response semantic correctness matters for this demo.
