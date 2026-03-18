# Troubleshooting Codex CAO Approval Prompts

This page covers one specific failure mode for CAO-backed Codex sessions: the live session starts, but the first real prompt turn stops on an operator approval menu instead of completing the requested action.

## Observed Version

This failure was reproduced in this workspace with locally installed `codex-cli 0.115.0`.

Treat that as the confirmed observed version for this guide, not as proof that the issue is limited to `0.115.0` only.

Typical blocked surface:

```text
› 1. Yes, proceed (y)
  2. Yes, and don't ask again for these files (a)
  3. No, and tell Codex what to do differently (esc)
```

## When This Guide Applies

Use this guide when all of the following are true:

- the session backend is `cao_rest`,
- the tool is `codex`,
- the CAO-backed tmux session starts successfully,
- a later prompt turn blocks on Codex approval or sandbox interaction,
- you expected the session to run without an operator approval menu.

This is the common shape seen in demo or runtime flows that rely on Codex skill execution inside a copied workspace.

## The Important Boundary

For CAO-backed Codex, Houmao does not launch the final interactive `codex` command line directly.

- Houmao builds the launch plan and runtime home.
- Houmao starts a CAO terminal with `provider=codex` and an installed CAO agent profile.
- CAO's Codex provider then constructs and sends the live `codex --no-alt-screen --disable shell_snapshot ...` command inside tmux.

That boundary matters because adapter `launch.args` are not the authoritative fix for this problem in `cao_rest`.

You may still see `launch_plan.args` in the Houmao session manifest, but that alone does not prove those args reached the actual interactive Codex process used by CAO.

## The Wrong Fix

Do not treat this as a CAO-source problem by default.

Two tempting fixes are usually wrong for this case:

- adding `--dangerously-bypass-approvals-and-sandbox` to Houmao's Codex tool adapter,
- patching the tracked CAO Codex provider just to force that flag into every interactive launch.

Why they are wrong here:

- For `cao_rest`, the actual interactive command is assembled by CAO's provider layer, not by Houmao's adapter args.
- Houmao already has a documented Codex bootstrap contract for approval and sandbox posture.
- This is normally a configuration-policy problem, not a CAO vendor bug.

## The Right Fix

Route the policy through the selected Codex config profile.

The supported path is:

1. add the desired Codex policy keys to the selected config profile under `tests/fixtures/agents/brains/cli-configs/codex/<profile>/config.toml`,
2. restart the session so Houmao rebuilds the runtime Codex home,
3. let `ensure_codex_home_bootstrap()` project those keys into the runtime-owned `CODEX_HOME/config.toml`.

For the "do not ask, no sandbox" posture, the relevant config is:

```toml
approval_policy = "never"
sandbox_mode = "danger-full-access"
```

This matches the runtime contract already used by Houmao for Codex launches:

- always seed trust for the launch workspace,
- always seed required notice state,
- only re-assert `approval_policy` and `sandbox_mode` when those keys are explicitly present in the selected Codex config profile.

## Why This Works

Houmao applies the same Codex bootstrap contract for:

- `codex_headless`,
- `codex_app_server`,
- Codex `cao_rest`.

That bootstrap edits the generated runtime `CODEX_HOME/config.toml` before launch. For CAO-backed Codex, this lets the live interactive process inherit the intended approval and sandbox posture without requiring Houmao to own CAO's command-construction internals.

## Recommended Verification

After changing the profile, do a fresh stop/start of the affected session and check the runtime-owned artifacts instead of assuming the fix took effect.

Verify these points:

1. The selected Codex config profile contains the intended keys.
2. The rebuilt runtime home contains those same keys in `CODEX_HOME/config.toml`.
3. The prompt turn no longer surfaces an operator approval menu.
4. The expected side effect or output completes successfully.

For CAO-backed sessions, it is normal for the session manifest to show `launch_plan.args: []` after this fix. The approval posture is coming from runtime-home config, not extra CLI flags.

## Practical Debugging Checklist

If the prompt still blocks, check these in order:

1. Confirm you restarted the session after editing the config profile. Old live sessions keep their previously generated runtime home.
2. Confirm you edited the profile that the selected brain recipe actually uses.
3. Open the generated runtime `config.toml` and verify the keys were projected there.
4. Inspect the live tmux pane to distinguish a true approval prompt from some other blocked surface.
5. Only investigate CAO source behavior after you have ruled out profile selection, runtime-home regeneration, and trust/bootstrap projection.

## Source References

- [`src/houmao/agents/realm_controller/backends/codex_bootstrap.py`](../../../../src/houmao/agents/realm_controller/backends/codex_bootstrap.py)
- [`docs/reference/realm_controller.md`](../../realm_controller.md)
- [`docs/reference/agents/operations/session-and-message-flows.md`](../operations/session-and-message-flows.md)
- [`tests/fixtures/agents/brains/cli-configs/codex/default/config.toml`](../../../../tests/fixtures/agents/brains/cli-configs/codex/default/config.toml)
