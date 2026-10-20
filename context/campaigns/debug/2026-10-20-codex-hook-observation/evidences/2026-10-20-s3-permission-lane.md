# Evidence: S3 permission lane (codex-cli 0.163.0, openlux-auto permission launcher)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Arm: S3. Key question: [KQ-4](../key-questions/KQ-4-blocked-state-permission.md).

## Run Identity

| Component | Value |
| --- | --- |
| Deliverable run | `tmp/codex-hook-capture/s3/run-20261020T043111Z/` (tmux `codexhook-s3-2976960`, pane `%191`) |
| Flawed attempt 1 | `tmp/codex-hook-capture/s3/run-20261020T043014Z/` (no session; relative `--launcher` path did not resolve in the scratch workdir) |
| Launcher | `tmp/codex-hook-capture/launchers/codex-openlux-permission`, built by `sed` removing `--dangerously-bypass-approvals-and-sandbox` from a copy of `~/.local/bin/codex-openlux-auto` (programmatic edit only; the key line was never read or printed). Verified with `grep -c dangerously` = 0 and `bash -n` = ok. |
| Lane flags | `-c approval_policy="on-request" -c sandbox_mode="read-only" --dangerously-bypass-hook-trust` |
| Why read-only | workspace-write always includes `/tmp` (`protocol.rs get_writable_roots_with_cwd`), so the frozen `/tmp` writes would execute without a prompt. Read-only forces the approval flow. |
| Collector | gen 1, port 40419 |
| Recording | 944 samples at 0.2 s (the long tail is the driver's 180 s Stop wait after the manual deny); non-empty, not tainted |
| Labels | `s3-permission-allow`, `s3-permission-deny`, `s3-deny-key-discovery` filled with digests |

Command:

```bash
pixi run python scripts/explore/codex-hook-observation/run_capture.py \
  --scenario s3 \
  --launcher /data/huangzhe/code/houmao/tmp/codex-hook-capture/launchers/codex-openlux-permission \
  --allow-permission-lane
```

## Modal Rendering (live, verbatim)

Allow prompt:

```text
  Would you like to run the following command?

  Environment: local

  Reason: May I write the requested file in /tmp? The session
  filesystem is read-only.

  $ printf 'hello\n' > /tmp/houmao-codex-hook-allow.txt

› 1. Yes, proceed (y)
  2. Yes, and don't ask again for commands that start with `printf
     'hello\n' > /tmp/houmao-codex-hook-allow.txt` (p)
  3. No, and tell Codex what to do differently (esc)

  Press enter to confirm or esc to cancel
```

The deny prompt is identical except for the `deny.txt` path. **There is no `No, continue without running it` option in this sandbox-escalation modal**, so the `d` shortcut is unbound. The deny key is **Escape** (option 3). The driver's blind `d` had no effect; the manual Escape at 04:32:17.621 selected option 3. This is recorded in `notes/manual-intervention.json`.

## Ordered Event Sequence

| Seq | Event | received_at_utc | turn_id | Key fields |
| --- | --- | --- | --- | --- |
| 1 | `SessionStart` | 04:31:18.357 | - | `source: startup`, `permission_mode: default` |
| 2 | `UserPromptSubmit` | 04:31:18.414 | `01a15793-fb07-7102-afcd-2dc1973c2722` | allow prompt |
| 3 | `PreToolUse` | 04:31:24.849 | same | `tool_name: Bash`, `tool_use_id: exec-c30a2560-0e8c-4406-89db-4473059e051b`, `tool_input: {"command": "printf 'hello\\n' > /tmp/houmao-codex-hook-allow.txt"}` |
| 4 | `PermissionRequest` | 04:31:24.903 | same | `tool_name: Bash`, **no `tool_use_id`**, `tool_input` adds `"description": "May I write the requested file in /tmp? The session filesystem is read-only."` |
| 5 | `PostToolUse` | 04:31:25.360 | same | same `tool_use_id` as #3, `tool_response: ""` |
| 6 | `Stop` | 04:31:34.006 | same | created-file answer |
| 7 | `UserPromptSubmit` | 04:31:34.520 | `01a15794-3a37-76e2-90a7-72c35319f34a` | deny prompt |
| 8 | `PreToolUse` | 04:31:40.792 | same | `tool_use_id: exec-eb6d114e-f359-48f5-8332-446e5aaa60d1`, command for `deny.txt` |
| 9 | `PermissionRequest` | 04:31:40.856 | same | same shape, no `tool_use_id` |
| 10 | `Interrupt` | 04:32:17.684 | same | no reason field |
| 11 | `SessionEnd` | 04:34:42.620 | - | `reason: "other"` after `/quit` |

No `Stop` after the deny. No `PostToolUse` for the denied command. `/tmp/houmao-codex-hook-allow.txt` exists with `hello\n`; `/tmp/houmao-codex-hook-deny.txt` does not exist.

## KQ-4 Verdicts

**P4.1: PermissionRequest fires before the modal paints. SUPPORTED.**
The hook was received at 04:31:24.903; the first 5 fps pane sample containing the modal is `s000060` at 04:31:25 (recorder elapsed 14.11), and the driver pressed `y` at 04:31:25.290. The hook therefore precedes the first captured modal frame and the keypress. The recorder's nominal 0.2 s interval and the second-granularity manifest do not resolve the exact paint instant, but the source path awaits the permission hooks before `request_reviewer_approval`, which is consistent with hook-first ordering. Treat this as a timing-bounded confirmation, not a millisecond proof.

**P4.2: on allow, the next event is the paired PreToolUse. REFUTED.**
`PreToolUse` for the call arrives **before** `PermissionRequest` (04:31:24.849 vs 04:31:24.903, 54 ms earlier). On allow, the next hook event after the approval is `PostToolUse` (04:31:25.360) with the **same `tool_use_id`** as the preceding `PreToolUse`. There is no second `PreToolUse` after approval.
Blocked interval: `PermissionRequest` 04:31:24.903 to `PostToolUse` 04:31:25.360 = **457 ms**; keypress `y` 04:31:25.290 to `PostToolUse` = **70 ms**; `PreToolUse` to `PostToolUse` = **511 ms**.

**P4.3: on deny, exactly what settles. `Interrupt` only; no `PostToolUse`, no `Stop`.**
Cancel/deny (Escape) was sent at 04:32:17.621; `Interrupt` arrived at 04:32:17.684 (63 ms later) with the same `turn_id` and no reason field. The TUI showed `✗ You canceled the request to run ...`, a red `Failed (exit 1)` transcript line, and `■ Conversation interrupted`. The first and only event after the deny is `Interrupt`; no `PostToolUse` and no `Stop` follow. A reducer must settle the blocked call at `Interrupt`, not wait for a tool result or a normal turn completion.

**P4.5: candidate rule "next PreToolUse with equal tool_name in the same turn_id". REFUTED.**
`PreToolUse` precedes `PermissionRequest`, so "next PreToolUse" would pair the allow request (`turn_id` `01a15793…`, command `allow.txt`) with the next turn's `PreToolUse` (`turn_id` `01a15794…`, command `deny.txt`), which is wrong. The empirically valid correlation is:

- Within a turn, the `PermissionRequest` belongs to the **immediately preceding** `PreToolUse` with the same `turn_id` and `tool_name` and a matching `tool_input.command`.
- `PermissionRequest` has no `tool_use_id`, so the Pre/Post pair is joined by the `tool_use_id` present on both tool events.
- With two approval cycles in one session, both cycles match one-to-one: (Pre#3, PermissionRequest#4, Post#5) for allow and (Pre#8, PermissionRequest#9, Interrupt#10) for deny.

`permission_mode` was **`default`** on every event, not `bypassPermissions`. `transcript_path` was non-null.

## Payload Inventory vs Schema

| Event | Live fields | Schema-optional absent | Notes |
| --- | --- | --- | --- |
| `PermissionRequest` | `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `tool_input`, `tool_name`, `transcript_path`, `turn_id` | `agent_id`, `agent_type` | **no `tool_use_id`**; `tool_input` carries `command` plus a `description` justification not present on `PreToolUse` |
| `PreToolUse` | `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `tool_input`, `tool_name`, `tool_use_id`, `transcript_path`, `turn_id` | `agent_id`, `agent_type` | `tool_input` has `command` only |
| `PostToolUse` | full set plus `tool_response` | `agent_id`, `agent_type` | `tool_response` is `""` (empty string) on allow |
| `Interrupt` | `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `transcript_path`, `turn_id` | - | no reason |

All schema `required` fields were present; the only schema-optional omissions were the subagent fields.

## Driver Fixes

1. **Absolute launcher path.** Attempt 1 failed because the wrapper is exec'd with the scratch workdir as cwd; a relative `--launcher` path did not resolve there. `main()` now calls `.resolve()` on the launcher. This was the first and only attempt that produced no session.
2. **Deny key auto-detection.** The driver sent `d`, which is unbound in the sandbox-escalation modal. `_permission_step()` now uses `d` only when `No, continue without running it` is present, otherwise `Escape`; the S3 deny step passes `key="auto"`.
3. **Deny settle wait.** `run_s3` now waits for `Interrupt` (and a bounded 5 s check for `Stop#2`) instead of a 180 s `Stop` wait. The deliverable run used the old wait, which is why it idled from 04:32:17 to 04:34:42 after the interrupt; the hook evidence is unaffected.
4. **Modal markers.** Added the live title `Would you like to run the following command` and the Cancel option `No, and tell Codex what to do differently`.

## Cleanup

The session was exited via `/quit` at 04:34:42.561; `SessionEnd` arrived 59 ms later. No tmux session, collector, or recorder processes remain. `/tmp/houmao-codex-hook-allow.txt` remains as scenario proof (content `hello\n`); `/tmp/houmao-codex-hook-deny.txt` is absent by design.
