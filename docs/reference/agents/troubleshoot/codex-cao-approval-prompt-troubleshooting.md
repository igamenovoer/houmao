# Troubleshooting Codex Approval Prompts (Legacy `cao_rest` Backend)

> **Legacy notice:** This troubleshooting page applies to the `cao_rest` backend, which is planned for removal. For new sessions, use the `local_interactive` backend where Codex launch is directly controlled.

This page covers one specific failure mode for `cao_rest`-backed Codex sessions: the live session starts, but the first real prompt turn stops on an operator approval menu instead of completing the requested action.

## Observed Version

This failure was reproduced in this workspace with locally installed `codex-cli 0.116.0` on 2026-03-23.

Treat that as the confirmed observed version for this guide, not as proof that the issue is limited to `0.116.0` only.

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
- Houmao already has a documented unattended launch-policy contract for Codex approval and sandbox posture.
- This is normally a configuration-policy problem, not a CAO vendor bug.

## The Right Fix

Route the posture through Houmao's first-class unattended launch policy instead of ad hoc adapter args or per-profile bootstrap assumptions.

The supported path is:

1. set `launch_policy.operator_prompt_mode: unattended` in the selected brain recipe, or pass `--operator-prompt-mode unattended` when building the brain,
2. restart the session so Houmao rebuilds the runtime home and re-resolves the launch plan,
3. let the shared launch-policy registry select the versioned Codex strategy for the detected installed CLI.

For the currently validated installed version `codex-cli 0.116.0`, Houmao resolves strategy `codex-unattended-0.116.x`. That strategy seeds the runtime-owned `CODEX_HOME/config.toml` with:

```toml
approval_policy = "never"
sandbox_mode = "danger-full-access"

[notice]
hide_full_access_warning = true

[notice.model_migrations]
"gpt-5.3-codex" = "gpt-5.4"
```

It also seeds trust under `[projects."<resolved-workdir>"].trust_level = "trusted"`.

## Why This Works

Houmao applies the same versioned unattended strategy selection for:

- `codex_headless`,
- `codex_app_server`,
- Codex `cao_rest`,
- Codex `houmao_server_rest`,
- raw `launch.sh` execution for brains built with unattended mode.

The strategy edits the generated runtime `CODEX_HOME/config.toml` before launch-plan execution. For CAO-backed Codex, this lets the live interactive process inherit the intended approval and sandbox posture without requiring Houmao to own CAO's command-construction internals.

## Recommended Verification

After changing the profile, do a fresh stop/start of the affected session and check the runtime-owned artifacts instead of assuming the fix took effect.

Verify these points:

1. The built manifest records `launch_policy.operator_prompt_mode: unattended`.
2. The session manifest or `start-session --json` output records `launch_policy_provenance.selected_strategy_id = "codex-unattended-0.116.x"` for the current installed version.
3. The rebuilt runtime home contains the expected runtime-owned keys in `CODEX_HOME/config.toml`.
4. The prompt turn no longer surfaces an operator approval menu.
5. The expected side effect or output completes successfully.

For CAO-backed sessions, it is normal for the session manifest to show no Codex-specific approval CLI flags. The approval posture is coming from runtime-owned config plus typed launch-policy provenance, not extra CAO command-line arguments.

## Practical Debugging Checklist

If the prompt still blocks, check these in order:

1. Confirm you restarted the session after enabling unattended mode. Old live sessions keep their previously generated runtime home and launch plan.
2. Confirm the selected recipe or build command actually requested `operator_prompt_mode = unattended`.
3. Open the generated runtime `config.toml` and verify the runtime-owned keys were projected there.
4. Inspect `launch_policy_provenance` to verify the detected version and selected strategy.
5. Inspect the live tmux pane to distinguish a true approval prompt from some other blocked surface.
6. Only investigate CAO source behavior after you have ruled out launch-policy mode, runtime-home regeneration, strategy selection, and trust/config synthesis.

## Source References

- [`src/houmao/agents/launch_policy/`](../../../../src/houmao/agents/launch_policy/)
- [`docs/reference/realm_controller.md`](../../realm_controller.md)
- [`docs/reference/agents/operations/session-and-message-flows.md`](../operations/session-and-message-flows.md)
- [`openspec/changes/add-versioned-unattended-brain-launch-policy/verification/live-validation-matrix.md`](../../../../openspec/changes/add-versioned-unattended-brain-launch-policy/verification/live-validation-matrix.md)
