## Why

Serverless managed-agent launches currently succeed and still print `open terminal failed: not a terminal` when the caller is non-interactive, because the CLI blindly attempts a tmux attach after the runtime is already live. Separately, normal control commands such as `agents state` and `agents gateway status` can race each other while resuming unattended Claude sessions and rewriting provider-owned JSON state, producing transient malformed-state failures during routine operations.

Both issues were reproduced in live testing and one of them was proven with log injection. They weaken the core `houmao-mgr` local-runtime workflow, so the runtime and CLI contracts need to be tightened before more serverless agent flows build on them.

## What Changes

- Change `houmao-mgr agents launch` so interactive launch success does not depend on attaching tmux when the caller has no usable TTY.
- Make the launch handoff path resolve and control tmux through the repo-owned libtmux-first integration whenever practical, using libtmux-owned command dispatch for remaining tmux operations when needed.
- Stop ordinary resume/control flows from non-atomically rewriting unattended provider bootstrap files such as Claude `settings.json` and `.claude.json`.
- Separate unattended pre-launch provider-state bootstrap from read-only or already-live resume/control flows, or otherwise require serialized and atomic provider-state mutation when a resumed control path must still repair owned state.
- Ensure concurrent local control commands against the same managed session fail closed or serialize safely instead of surfacing transient malformed provider-state reads.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-agents-launch`: interactive launch handoff behavior changes so non-interactive callers get a successful launch result without a false tmux-attach failure.
- `brain-launch-runtime`: resumed local control for unattended sessions changes so provider-owned bootstrap state is not unsafely rewritten during ordinary resume/control operations.
- `tmux-integration-runtime`: tmux attach and handoff behavior is clarified under the libtmux-first integration boundary instead of relying on ad hoc raw tmux subprocess calls.

## Impact

- Affected code includes `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/srv_ctrl/commands/managed_agents.py`, `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/realm_controller/launch_plan.py`, `src/houmao/agents/launch_policy/provider_hooks.py`, and tmux integration helpers.
- Operator-visible CLI behavior changes for non-interactive `houmao-mgr agents launch` callers.
- Runtime concurrency behavior changes for unattended provider-state bootstrap on resumed local control paths.
- Verification will need targeted unit coverage plus live concurrency and non-interactive launch repros for Claude-managed local interactive sessions.
