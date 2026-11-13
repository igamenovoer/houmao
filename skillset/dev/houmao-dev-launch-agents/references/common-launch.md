# Common Development Launch Contract

## Workflow

1. **Resolve inputs** using **Launch Inputs** and [credential-resolution.md](credential-resolution.md).
2. **Prepare a private run** using **Shared Preparation**. Keep generated homes and credentials outside the checkout.
3. **Select the execution path** from **Raw TUI Execution** or [../commands/launch-fixture.md](../commands/launch-fixture.md) for headless and managed lanes.
4. **Launch and verify** the captured process and authority using **Startup Verification**. Preserve the requested workdir, posture, and ownership.
5. **Write safe launch evidence** using **Evidence and Cleanup**, then return the actual identity, attach command when applicable, and scoped cleanup command.

If a test needs additional native arguments or a maintained harness, use the native planning tool to map the requested behavior to prepared fixture inputs and the supported launch surface, then execute that plan without changing credential selection or launch ownership.

## Launch Inputs

Resolve the client, API case or imported native bundle, explicit model metadata, surface, mode, permission posture, and any requested workdir/session. Provider-specific commands mean raw TUI, with unattended posture by default. Unattended TUI is still interactive terminal execution; it is not headless mode.

With no requested workdir or session name, use the helper's fresh private workdir and generated session name. For an exact trusted workdir/session, explicit `as_is` posture, or additional native arguments, use **Exact-Workdir TUI Adapter**. Never silently ignore such inputs. A requested session name must be unused; report a collision or agree on a fresh name without replacing the existing session.

Resolve the repository root and selected executable path, capture `--version`, and check tmux when required. Preserve inherited proxy settings without printing values or assuming a proxy address. A model, initial prompt, resume target, extra writable directory, or native argument requires explicit selection or delegated judgment. Native arguments must not override the selected credential/home/endpoint, switch mode, carry secrets, or contradict the permission posture.

## Shared Preparation

Use the repository's [fixture helper](../../../../scripts/agents/test-fixtures/README.md) rather than implementing another credential parser, provider configuration generator, or managed launch protocol. Run its Python entrypoint through Pixi from the checkout. For example, after configuring the selected cloud file:

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case cloud-api --client codex --surface raw --mode tui \
  --env-file "$HOME/.config/houmao/test-fixtures/deepseek.env"
```

Replace the client and case with the selected values. For native auth, replace `--case` and `--env-file` with `--auth-method native-login --auth-bundle NAME` and an explicit `--auth-root` when needed. Supply supported model/context/reasoning overrides only when selected. For an alternate resolved executable, use `--executable PATH`.

Capture `run_dir` from the result. It owns `home/`, `assets/`, `workdir/`, `private-env.json`, and `run.json`. Runs default to `${XDG_STATE_HOME:-~/.local/state}/houmao/test-fixtures/runs/`; explicit `--run-root` or `HOUMAO_TEST_RUN_ROOT` must also be external. Source auth and reusable imports remain unchanged. Preparation is offline and validates imported native content; a native configuration check alone does not validate the bundle or prove live authentication.

Stage only test-authorized inputs in the workdir before launch. Raw preparation does not initialize Git automatically; initialize the disposable project only when the test requires it. The fixture helper does not install the caller's skill pack or adjudicate its oracle.

## Raw TUI Execution

### Helper-Owned Session

Use this path when the helper's generated workdir, session name, and unattended policy satisfy the request:

```bash
pixi run python scripts/agents/test-fixtures/fixture.py launch --run-dir /external/prepared-run
```

Read `identity.tmux_session_name` from the result, then resolve the actual pane with `tmux list-panes`. Verify startup before sending a requested prompt. Use the helper's `stop` command for this session.

### Exact-Workdir TUI Adapter

The helper does not accept `--workdir`, `--session-name`, `as_is`, or arbitrary native arguments. For these raw TUI requests, keep preparation unchanged and run a small adapter inside the private run. Do not rewrite `run.json` to reference an external workdir: `load_run` deliberately rejects that mutation.

Write a mode-`0600` `tui-request.json` containing absolute `repo_root`, `prepared_run`, and trusted existing `workdir` paths, `posture` (`unattended` or `as_is`), and a vetted `extra_args` string array. The request contains no secrets. Write this mode-`0700` `launch-provider.py` beside it:

```python
"""Execute a prepared raw TUI in the explicitly selected test workdir."""

import json
import os
from pathlib import Path
import sys

os.umask(0o077)
request = json.loads(Path(sys.argv[1]).read_text())
repo = Path(request["repo_root"]).resolve(strict=True)
sys.path.insert(0, str(repo / "scripts/agents/test-fixtures"))

from fixturelib.launch import raw_command, run_environment
from fixturelib.prepare import load_run

run = load_run(Path(request["prepared_run"]))
config = run["configuration"]
if config["surface"] != "raw" or config["mode"] != "tui":
    raise ValueError("The adapter requires a prepared raw TUI")
argv = raw_command(run)
posture = request["posture"]
if posture == "as_is":
    bypass = {
        "claude": "--dangerously-skip-permissions",
        "codex": "--dangerously-bypass-approvals-and-sandbox",
        "kimi": "--auto",
    }[config["client"]]
    argv.remove(bypass)
elif posture != "unattended":
    raise ValueError("Unknown permission posture")
argv.extend(request.get("extra_args", []))
env = run_environment(run)
os.chdir(Path(request["workdir"]).resolve(strict=True))
os.execvpe(argv[0], argv, env)
```

Resolve the managed interpreter once with `pixi run python -c 'import sys; print(sys.executable)'`. Build a shell pane command from that absolute interpreter, adapter path, and request path using `shlex.join`, prefixed with `exec`. Pass it to `tmux new-session -d -s NAME -c WORKDIR` using a structured subprocess argument list. Do not run `pixi run` inside the pane: its project directory handling can change the requested workdir. Keys are loaded inside the child through `run_environment`; they never become tmux command arguments.

The skill owns this custom session. Record `owner: skill-adapter`, the exact session and pane, selected workdir, and prepared run path in `launch.json`. The helper run remains `prepared`, and `fixture.py stop` cannot stop this custom session. Use `tmux kill-session -t CAPTURED_NAME` for its cleanup. Do not call the helper's `launch`, `prompt`, or `stop` on this adapter session. Send any explicitly requested interaction to the verified pane through the calling workflow's input surface.

## Startup Verification

Use a bounded startup interval. Check that the captured session and pane exist, their process tree contains the selected client, and visible pane text shows its TUI. A live tmux session alone does not establish readiness. An unattended login, permission, migration, or configuration prompt is a failed/incomplete startup; do not click through it as routine setup.

For exact-workdir launches, verify the client's actual working directory. Capture diagnostics privately and inspect them before sharing a sanitized finding. A successful startup is not proof of a completed model turn. Headless and managed completion checks belong to the selected fixture launch routine.

## Evidence and Cleanup

Keep `launch.json` and `launch-report.md` in the private run, alongside the helper's `run.json` and `report.json`. Include schema version, client/version/executable path, selected route and source path/reference names, explicit model metadata, surface/mode/posture, actual workdir, owner, session/pane or managed identity, verification result, private diagnostic paths, and the scoped cleanup command. Return an attach command only for a verified live TUI.

A caller may request `<test-run>/launch/` inside the checkout. Write only sanitized launch metadata/report or a pointer there; keep generated homes, env files, credential copies, native output, and mutable private state external. Record explicit arguments only after checking that they contain no secrets. Do not copy the complete run tree into a repository-local report.

Cleanup only the captured authority: helper-owned runs use `fixture.py stop --run-dir PATH`; adapter-owned sessions use their recorded tmux name. Retain failure evidence and report failed cleanup. Do not stop a shared tmux server, unrelated session, or pre-existing passive server.

## Maintained Harnesses

When the test subject needs a demo's additional behavior, use its maintained entrypoint and explicit fixture inputs: [minimal launch](../../../../scripts/demo/minimal-agent-launch/tut-agent-launch-minimal.md), [shared TUI tracking](../../../../scripts/demo/shared-tui-tracking-demo-pack/README.md), or the `houmao-dev-tui-testing` recorder workflow. Let that harness own its lifecycle. Do not duplicate its launch or claim a raw session has a managed identity.
