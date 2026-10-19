# Live Smoke Qualification — CLI Hook Observation Channel

Date: 2026-10-20. Change: `add-cli-hook-observation-channel` (implementation commit `0501d119`). Campaign: [2026-10-19-claude-hook-observation](../debug-intent.md). This report is evidence only; no product code was changed.

## Scope and Method

The campaign exercised the opt-in managed Claude channel at the host version (2.1.303) and the support floor (2.1.296). Each scenario used one managed `local_interactive` session per version leg (14 sessions total; the latest compaction leg performed a second compaction inside the same session). Prompts were the frozen short texts from the 2026-10-19 campaign where they fit. All evidence is under `tmp/hook-observation-smoke/<scenario>-<version>/` in the qualification layout (`manifest.json`, `channel-status.ndjson`, `hook-events.ndjson`, `merged-state.ndjson`, `admission-decisions.ndjson`, `cleanup.json`, `report.md`, plus state snapshots and channel-file copies).

The channel was enabled by exporting `HOUMAO_HOOK_OBSERVATION_CLAUDE=1` in the process that ran `houmao-mgr project agents launch`. The collector, hook block, and event store were created by the production launch path; no harness shim injected hooks.

## Launch Mechanism

Managed launches were created with `houmao-mgr project agents launch --specialist <name> --gateway-background` from a scratch project overlay at `tmp/hook-observation-smoke/project`. Two specialists were used:

- `smoke-claude-unattended`: the maintained unattended posture (launch policy adds `--dangerously-skip-permissions` and seeds workspace trust).
- `smoke-claude`: `prompt_mode: as_is` (`--no-unattended`), used only for the permission scenario so the provider runs without skip-permissions. Because `as_is` skips the launch policy, it also skips `claude.ensure_project_trust`.

The provider binary was selected with a PATH shim because the managed launch resolves `claude` from the launch PATH and publishes that PATH into the tmux session environment:

- latest: `tmp/hook-observation-smoke/bin/latest/claude` -> `/home/huangzhe/.bun/bin/claude` (2.1.303).
- floor: `tmp/hook-observation-smoke/bin/floor/claude` -> `tmp/hook-capture/floor-2.1.296/install/node_modules/.bin/claude` (2.1.296).

Both shims replicate the DeepSeek credential lane at runtime and never print or embed the key. Version confirmation is recorded in `normal-latest/version-verification.txt` and `normal-floor/version-verification.txt`; the observed pane banners were `Claude Code v2.1.303` and `Claude Code v2.1.296`.

Tracked state was read from the attached gateway's `GET /v1/control/tui/state`; admission was exercised through `houmao-mgr agents single ... gateway prompt` with `ready-only` and `if-no-pending`.

## Results Matrix

| Scenario | 2.1.303 | 2.1.296 | Evidence pack |
| --- | --- | --- | --- |
| Normal turn | PASS | PASS | `normal-latest/`, `normal-floor/` |
| Direct pane input | PASS | PASS | `direct-input-latest/`, `direct-input-floor/` |
| Permission wait + admission | PASS | PASS | `permission-latest/`, `permission-floor/` |
| Compaction | **PASS** (rerun `e59b05bd`; originally D1) | **PASS** (rerun `e59b05bd`; originally D1) | `compaction-latest-rerun/`, `compaction-floor-rerun/`; original `compaction-latest/`, `compaction-floor/` |
| Stop/relaunch | PASS (D3 note) | PASS (D3 note) | `stop-relaunch-latest/`, `stop-relaunch-floor/` |
| Collector kill | **PASS** (rerun `e59b05bd`; originally D2) | **PASS** (rerun `e59b05bd`; originally D2) | `collector-kill-latest-rerun/`, `collector-kill-floor-rerun/`; original `collector-kill-latest/`, `collector-kill-floor/` |
| Hooks disabled | PASS | PASS | `hooks-disabled-latest/`, `hooks-disabled-floor/` |
| Untrusted workspace (inspection) | PASS (D6 gap) | PASS (D6 gap) | `untrusted-latest/`, `untrusted-floor/` |

The channel installed, authenticated, and delivered events in every launched session where the flag was set. Every launched agent remained controllable through the TUI, including in the originally failed compaction scenario and after collector death; both rerun legs passed after `e59b05bd` (see the rerun section below).

## Per-Scenario Evidence

### Normal Turn

Frozen prompt: `Reply with exactly: OK`, submitted through the gateway with `ready_only`.

- 2.1.303: events `SessionStart` (seq 1), `UserPromptSubmit` (seq 2), `PostToolUse` (seq 3), `Stop` (seq 4). `turn.phase` changed `ready -> active` at submission and `active -> ready` on Stop; `last_turn.result=success`, `last_turn.source=explicit_input`, `work=clear`, `settled=true`.
- 2.1.296: events `SessionStart`, `UserPromptSubmit`, `Stop` (no tool event in this short turn); same merged result.

Evidence: `normal-latest/merged-state.ndjson` (`launched`, `active_prompt_submitted`, `completed_success`), `normal-latest/hook-events-summary.json`, `normal-floor/` equivalents.

### Direct Pane Input

Frozen prompt: `Reply with exactly: OK`, typed with `tmux send-keys` into the `agent` pane. No gateway submission existed.

- Both versions: `UserPromptSubmit` armed the turn from direct input; `Stop` settled it. `last_turn.source=hook_observation` (the key distinction from the gateway path), `work=clear`, `settled=true`.
- Latest event sequence: `SessionStart`, `UserPromptSubmit`, `PostToolUse`, `Stop`.
- `admission-decisions.ndjson` records `not_applicable` because no gateway admission path was used.

Evidence: `direct-input-latest/merged-state.ndjson` (`completed_success` with source `hook_observation`), `direct-input-floor/`, `hook-events-summary.json`.

### Permission Wait and Admission

Frozen prompt: `Create a file named /tmp/houmao-hook-allow.txt containing hello`. The file already existed from the prior campaign, so the provider first asked to read the managed memo, then to read the target file; the write itself failed with `Error writing file` (the provider still reported the file already contained `hello`).

Procedure per version: accept the workspace-trust dialog (as_is only), select manual mode with Shift+Tab (both versions booted no-bypass launches into auto mode), submit with `admission-policy=always` because the manual-mode TUI surface axes are `unknown` (D4), then exercise admission while blocked.

Blocked state (both versions): `turn.phase=blocked`, `parsed_surface.input_mode=modal`, `business_state=awaiting_operator`, hook channel active, last event `PermissionRequest`.

Admission refusals while blocked:

| Version | Policy | Error code | Refusal fact |
| --- | --- | --- | --- |
| 2.1.303 | `ready_only` | `not_ready` | `turn.phase='blocked'`, `Hook observation: ... blocked=true` |
| 2.1.303 | `if_no_pending` | `pending_input_unknown` | `Hook observation: ... turn_phase='blocked', blocked=true` |
| 2.1.296 | `ready_only` | `not_ready` | same shape |
| 2.1.296 | `if_no_pending` | `pending_input_unknown` | same shape |

The `if_no_pending` refusal is emitted by the pending-input check before the hook gate, but the decision record still carries `blocked=true`; this is acceptable evidence that hook facts are attached to refusals, though the reason ordering is worth noting for UX.

Resolution: allowing the read modal (key `1`) produced `PostToolUse`, which cleared `blocked`; the final `Stop` settled `last_turn.result=success` with `work=clear`, `settled=true`. Latest events: `SessionStart`, `UserPromptSubmit`, `PermissionRequest`, `PostToolUse`, `PermissionRequest`, `PostToolUse`, `Stop` (8 including the generation boundary). Floor identical.

Evidence: `permission-latest/admission-decisions.ndjson`, `permission-latest/state-snapshots/blocked_read_permission.json`, `permission-latest/hook-events-summary.json`; `permission-floor/` equivalents.

### Compaction — FAILED in the Original Run (rerun PASS)

Frozen prompts: `Read README.md and summarize in one sentence.`, then `/compact` via `send-keys`, then `Reply with exactly: OK`. `README.md` was a three-line file created in the run workdir.

Hook delivery worked in both versions: `PreCompact` (`trigger=manual`), a compaction `SessionStart`, and `PostCompact` all arrived. `turn.phase` stayed `ready` across operator-invoked compaction with no armed prompt, and post-compaction turns completed normally.

The failure is the terminal outcome. The first turn settled `success` on Stop, but the merged state later overwrote it to `interrupted` with conflict reason `hook_success_tui_interrupted`; `last_turn.updated_at_utc` remained at the Stop time. No Esc or user interrupt occurred. The overwrite reproduced twice in the 2.1.303 session and once in the 2.1.296 session:

- 2.1.303, first compaction: Stop at `16:38:17Z`, overwrite transition at `16:38:17Z`, `PreCompact` at `16:38:20Z`, `PostCompact` at `16:38:28Z`.
- 2.1.303, second compaction: `PreCompact` seq 10 at `16:40:20Z`, `PostCompact` seq 12 at `16:40:35Z`; state at `16:40:37Z` was `interrupted` with `hook_success_tui_interrupted`.
- 2.1.296: Stop at `16:45:47Z`, `PreCompact` seq 7 at `16:45:52Z`, `PostCompact` seq 9 at `16:45:59Z`; the `maintenance_postcompact` snapshot at `16:45:59Z` was `interrupted`.

This violates the qualification expectation “Compaction … previous outcome preserved” and G7's “Compaction does not erase terminal outcomes”. The hook terminal latch itself is correct; the merge's documented TUI-interrupt exception is being fed false interrupt evidence by the compaction repaint. Post-compaction work still proceeds, so the defect is in published outcome, not session control.

Evidence: `compaction-latest/state-snapshots/post_compaction_interrupted.json`, `compaction-latest/state-snapshots/post_second_compaction_complete.json`, `compaction-latest/compaction-samples.ndjson`, `compaction-latest/hook-events-summary.json`, `compaction-floor/state-snapshots/maintenance_postcompact.json`, `compaction-floor/compaction-samples.ndjson`.

### Stop and Relaunch

Procedure: turn 1, `agents single stop`, `agents single relaunch --chat-session-mode new`, then turn 2.

Both versions:

- The relaunch reused the same session root and allocated channel generation 2; the event store retained generation-1 records and appended a new `SessionStart` at generation 2.
- Old-generation records were dropped by the reader. The 2.1.303 reader reported conflict `hook_orphan_generation` with `orphan_generations=0` (D7); the 2.1.296 run reported no conflict.
- After relaunch, `agents single state` showed `gateway_health=not_attached`; an explicit `gateway attach --background` was required before tracked state was observable (D3).
- Turn 2 settled `last_turn.result=success`, `work=clear`, `settled=true` in generation 2.
- The relaunch changed the tmux session name from the launch-time `hook-smoke-...` name to `HOUMAO-smoke-...-<epoch>`; cleanup checks used the authoritative state payload, not the launch-time name.

Evidence: `stop-relaunch-latest/channel-status.ndjson` (`launched` gen 1, `after_relaunch` gen 2), `stop-relaunch-latest/hook-events.ndjson` (both generations), `stop-relaunch-latest/merged-state.ndjson`; `stop-relaunch-floor/` equivalents.

### Collector Kill — FAILED in the Original Run (rerun PASS)

Procedure: turn 1 completed, then `SIGTERM` to the collector PID from `collector.json`, then turn 2 after the 30 s staleness threshold. Verdict: FAILED because the published channel state said `active` while the collector was dead; the TUI-only fallback itself worked.

Observed on both versions:

- The collector wrote `collector.json` with `status=stopped` and exited; the process was gone.
- `channel.json` still said `status=running` and `channel_state=active`, because the collector does not update it and the tracker reads only `channel.json`.
- While the TUI stayed stable, the tracker continued to report `active`; the last idle snapshot was `16:42:13Z`, 2 s after the kill, and nothing in the health path consults `collector.json`. The next turn at `16:42:51Z` changed the TUI and the first post-prompt sample was `stale`.
- Turn 2 was admitted (`ready_only`) and submitted; during the turn, once the TUI changed and the 30 s gap elapsed, the channel transitioned to `stale` with detail “No hook event arrived within the staleness threshold while the TUI kept changing” and conflict `hook_stale_tui_authoritative`.
- Turn 2 settled `last_turn.result=success` TUI-only; `work=unknown`, `settled=false`, no further hook events.
- On stop, `stop_collector` used `collector.json` and published `channel_state=stopped` in `channel.json`.

The session remained controllable and eventually degraded to `stale`, but the channel reported `active` while the collector was dead, and it never reached the terminal `stopped` state for an external kill. That is the wrong published channel state and is the reason this scenario is FAILED (D2). Degradation depends on staleness and TUI movement rather than collector liveness.

Evidence: `collector-kill-latest/channel-degradation.ndjson` (stale samples), `collector-kill-latest/state-snapshots/after_kill_idle.json`, `after_kill_turn2.json`, `collector-kill-latest/channel-files/stopped.collector.json`; `collector-kill-floor/` equivalents. The raw event store was removed by cleanup, so the event inventory in `hook-events-summary.json` is reconstructed from the `channel.json` stop snapshot and labeled as such.

### Hooks Disabled

The flag was unset for the launch. Both versions:

- No `hook-observation/` subtree under the session root.
- The managed home's `settings.json` has no `hooks` key.
- No collector process was started.
- `observation_channels=null`, `diagnostics.hook_channel_state=null`, `work=unknown`, `settled=false`.
- A TUI-only turn ran and reached `turn.phase=ready`; 2.1.303 published `last_turn.result=success` at the completion snapshot. 2.1.296 published success transiently and then cleared it to `none` after the TUI settle window; this is the pre-existing TUI-only behavior, not a hook-channel effect.

Evidence: `hooks-disabled-latest/`, `hooks-disabled-floor/` (`launched`, `completed_tui_only`, empty hook event files, `cleanup.json` with no hook subtree).

### Untrusted Workspace (Inspection)

Managed unattended launches seed trust before provider start. The `.claude.json` of the unattended normal runs contains `projects.<workdir>.hasTrustDialogAccepted=true` (`normal-latest` home `claude-brain-20261019-163713Z-947742`, `normal-floor` home `claude-brain-20261019-164346Z-e29f29`), and both sessions started at the prompt with no trust dialog. Evidence: `untrusted-latest/trust-inspection.json`, `untrusted-floor/trust-inspection.json`, and the seeded settings summaries showing all nine observer event hooks.

The `as_is` permission launches did show the workspace-trust dialog because trust seeding is a launch-policy action; the dialog was accepted manually, and the channel still reported `active` (not `untrusted_workspace`). This is the counterexample that explains why v1 has no `untrusted_workspace` producer (D6): the maintained managed path prevents the precondition rather than detecting it.

## Rerun After Fix e59b05bd (2026-10-20)

The two originally failed scenario legs were rerun at both versions after commit `e59b05bd` ("constrain TUI interrupt override by turn epoch, detect collector stop, persist hook latch through staleness"). Fresh evidence roots were used so the original packs remain intact.

| Rerun leg | Version | Verdict | Evidence |
| --- | --- | --- | --- |
| Compaction | 2.1.303 | **PASS** | `compaction-latest-rerun/` |
| Compaction | 2.1.296 | **PASS** | `compaction-floor-rerun/` |
| Collector kill | 2.1.303 | **PASS** | `collector-kill-latest-rerun/` |
| Collector kill | 2.1.296 | **PASS** | `collector-kill-floor-rerun/` |

### Compaction Rerun

The same frozen sequence was used: one completed turn, `/compact`, then one post-compaction turn. In both versions:

- The completed turn latched `last_turn.result=success`; its `updated_at_utc` was the Stop time (2.1.303 `17:06:14Z`, 2.1.296 `17:07:07Z`).
- Through `PreCompact`, the compaction `SessionStart` (`source=compact`), `PostCompact`, and an additional 8 s settle window, `last_turn.result` stayed `success` and `updated_at_utc` stayed at the Stop time.
- No `hook_success_tui_interrupted` conflict was published. The only conflict observed was `hook_terminal_tui_active` during the maintenance repaint window, which cleared once compaction finished.
- The channel stayed `active`; `work=clear`, `settled=true` at the settled snapshot; the post-compaction turn settled success.
- Hook stream: `PreCompact` seq 6, `SessionStart` seq 7 (`source=compact`), `PostCompact` seq 8, then the post-compaction `UserPromptSubmit`/`Stop` pair.

Evidence: `compaction-latest-rerun/state-snapshots/{turn1_completed,maintenance_precompact,maintenance_postcompact,post_compaction_settled}.json`, `compaction-latest-rerun/compaction-samples.ndjson`, `compaction-latest-rerun/conflicts.ndjson`, `compaction-latest-rerun/hook-events-summary.json`; the `compaction-floor-rerun/` equivalents. Per-leg reports: `compaction-latest-rerun/report.md`, `compaction-floor-rerun/report.md`.

### Collector Kill Rerun

The rerun completed turn 1, sent `SIGTERM` to the collector, and polled the gateway state every ~200 ms without changing the TUI.

- The channel left `active` and published `stopped` after **441 ms** (2.1.303) and **654 ms** (2.1.296), within one or two 0.5 s gateway poll cycles, with detail `The hook observation collector is stopped.` No 30 s staleness wait and no TUI change were required.
- The latched `last_turn.result=success` with the Stop timestamp persisted through the `stopped` channel state; `work=unknown`, `settled=false` as expected for a degraded channel.
- Turn 2 was admitted with `ready_only` and settled success TUI-only; the channel remained `stopped` and added no hook events.
- Recovery: after stop and `relaunch --chat-session-mode new`, the channel returned as generation 2 `active` with a new collector and `SessionStart`, and turn 3 settled success. The relaunch still requires the explicit `gateway attach` noted in D3.
- D7 check: after relaunch, `conflict_reasons=["hook_orphan_generation"]` and `counters.orphan_generations=6` agree; the counter now reflects the reader's dropped old-generation lines.

Evidence: `collector-kill-latest-rerun/channel-drop.ndjson` (441 ms kill-to-stopped timeline), `state-snapshots/{turn1_before_kill,after_kill_stopped,tui_only_turn,after_relaunch,after_relaunch_turn}.json`, `relaunch.json`, `gateway-attach.json`, `hook-events-summary.json`, `cleanup.json`; the `collector-kill-floor-rerun/` equivalents (654 ms). Per-leg reports: `collector-kill-latest-rerun/report.md`, `collector-kill-floor-rerun/report.md`.

The optional stale-retention check was not run as a separate arm because it would require a new session and a 30 s idle window; the same degraded-channel publication path was exercised live through the `stopped` state, where the latched success and Stop timestamp persisted. The original stale-window evidence (collector kill before the fix) remains in `collector-kill-latest/` and `collector-kill-floor/`.

## Admission Decision Records

The permission scenario is the only one that exercised admission against a hook posture. Full records are in `permission-latest/admission-decisions.ndjson` and `permission-floor/admission-decisions.ndjson`. Summary:

- `ready_only` at `turn.phase=blocked` refused with `not_ready`; detail included `turn_phase='blocked'` and `blocked=true`.
- `if_no_pending` at `turn.phase=blocked` refused with `pending_input_unknown`; detail included `turn_phase='blocked'` and `blocked=true`.
- Both refusals were exit code 1 with `sent=false` and structured JSON on stderr.
- No refusal was observed after collector death in the original run: `ready_only` admitted the next turn while the channel was still reported active, and the channel degraded to `stale` during that turn. This is consistent with “a degraded channel adds no refusal reasons”, although the admission itself happened before the stale transition was published. After `e59b05bd` the kill publishes `stopped`, which also adds no hook gate.

A `ready_only` admission attempt from the manual-mode permission session before any turn was also refused with `not_ready` because the TUI surface axes were `unknown` (D4), not because of a hook fact.

## Defects

### D1 — Compaction overwrites a hook-latched success with `interrupted` (major) — FIXED in `e59b05bd`

A normal completed turn (`Stop` → `last_turn.result=success`) is later mutated to `interrupted` with conflict `hook_success_tui_interrupted`. The trigger is false TUI temporal-interrupt evidence produced by the compaction repaint; no Esc or user abort occurred. `last_turn.updated_at_utc` keeps the Stop timestamp, so the mutation is silent apart from the conflict reason.

Reproduction: managed Claude session, one completed turn, `/compact` via the pane; watch `last_turn.result` and `observation_channels[0].conflict_reasons`. Reproduced at 2.1.303 (twice) and 2.1.296 (once). Evidence: `compaction-latest/state-snapshots/post_second_compaction_complete.json` (fields `last_turn.result`, `last_turn.updated_at_utc`, `observation_channels[0].conflict_reasons`), `compaction-latest/compaction-samples.ndjson`, `compaction-floor/state-snapshots/maintenance_postcompact.json`. This violated state-transitions section 4 (terminal latch) as exercised through the compaction scenario and G7.

Status: fixed in `e59b05bd` (turn-epoch scoping plus maintenance-window contamination rejection for the TUI interrupt override). The rerun at both versions passed and kept `success` with the Stop timestamp through compaction; see `compaction-latest-rerun/` and `compaction-floor-rerun/`.

### D2 — External collector death is not detected from `collector.json` (medium) — FIXED in `e59b05bd`

`collector.json` correctly records `status=stopped` after SIGTERM, but the tracker's health reader uses `channel.json`, which still says `running` and `channel_state=active`. The channel therefore stays `active` while the TUI is stable (no code path reads the collector liveness record); it only degrades to `stale` after the 30 s threshold plus a TUI change. The health state machine's terminal `stopped` state is reachable only through the session stop path (`stop_collector` marks the channel stopped). Evidence: `collector-kill-latest/state-snapshots/after_kill_idle.json` (active at `16:42:13Z`, kill at `16:42:11Z`), `collector-kill-latest/channel-files/` (`collector.json` stopped while `channel.json` running), `collector-kill-latest/channel-degradation.ndjson`.

Status: fixed in `e59b05bd` (the reader now consults the generation-matched `collector.json` liveness record). The rerun at both versions published `stopped` within one or two poll cycles (441 ms at 2.1.303, 654 ms at 2.1.296) with no TUI change; see `collector-kill-latest-rerun/` and `collector-kill-floor-rerun/`.

### D3 — Managed relaunch does not reattach the gateway and changes the tmux session name (medium, operational)

After `agents single relaunch`, `gateway_health=not_attached` and `request_admission=blocked_unavailable` until an explicit `gateway attach`. The new tmux session is named `HOUMAO-<agent>-<epoch>` instead of the launch-time `--session-name`. The channel itself is fine (generation 2, new collector, new SessionStart), but observation after relaunch requires an extra control-plane step. Evidence: `stop-relaunch-latest/relaunch.json`, `stop-relaunch-latest/gateway-attach.json`, `stop-relaunch-latest/launch.json` vs the `identity.tmux_session_name` in the attach payload.

### D4 — Manual-mode Claude TUI surface axes stay `unknown` (minor, TUI detector)

With the provider in manual permission mode (both 2.1.303 and 2.1.296), the parsed surface reports `business_state=idle`, `input_mode=freeform`, but `surface.accepting_input/editing_input/ready_posture/pending_input` are all `unknown`, and `turn.phase` is `unknown` until the hook latch supplies it. `ready_only` admission therefore refuses with `not_ready` even at an idle prompt; the permission scenario used `admission-policy=always` for the first submission. This is outside the hook channel (the hook path correctly reports `blocked` and `ready`), but it prevents a hook-only fix for manual-mode admission. Evidence: `permission-latest/state-snapshots/initial_after_manual_mode.json`, `permission-latest/admission-decisions.ndjson` (`prompt1_ready_only`), `permission-floor/state-snapshots/after_manual_mode.json`.

### D5 — `channel.json` counters lag during a live session (minor, observational)

`channel.json` is written at install and stop, not on every accepted event. During a live session it can show `counts.accepted` and `last_sequence` from the install snapshot while the tracker's reader has advanced (for example generation 2 showed accepted 4 / last_sequence 4 while the tracker reported sequence 8). The live counters in `observation_channels` are correct because they come from the reader; operators reading `channel.json` directly should not treat its counters as live. Evidence: `stop-relaunch-latest/channel-files/turn2_after_relaunch.channel.json` vs `stop-relaunch-latest/state-snapshots/turn2_after_relaunch.json`.

### D6 — No `untrusted_workspace` producer in v1 (minor, gap vs design wording)

The design risk table says workspace trust not seeded makes the channel report `untrusted_workspace`; no code path produces that state. Managed unattended launches seed trust, so the maintained path cannot reach it; an as_is launch that shows the trust dialog still reports `active`. The qualification scenario therefore verifies the precondition-prevention behavior and records the missing producer. Evidence: `untrusted-latest/`, `permission-latest/state-snapshots/` and the report note above.

### D7 — `hook_orphan_generation` note without a counter increment (minor) — FIXED in `e59b05bd`

After the 2.1.303 relaunch, `observation_channels[0].conflict_reasons` contained `hook_orphan_generation` while `counters.orphan_generations` stayed 0. The reader's initial-scan drop is expected; the diagnostic/counter inconsistency was cosmetic. Evidence: `stop-relaunch-latest/state-snapshots/after_relaunch.json`.

Status: fixed in `e59b05bd` (reader-dropped old-generation lines now feed the public counter). Both rerun relaunches reported `conflict_reasons=["hook_orphan_generation"]` with `orphan_generations=6`; see `collector-kill-latest-rerun/state-snapshots/after_relaunch.json` and the floor equivalent.

## Deviations

1. The permission lane used the `as_is` specialist and manual permission mode because the maintained unattended launch always passes `--dangerously-skip-permissions`, which suppresses permission modals. Both versions boot a no-bypass launch into auto mode; manual mode was selected with Shift+Tab. Modal keys observed: allow `1`, deny `3`.
2. The as_is launches showed the workspace-trust dialog (trust seeding lives in the launch policy); the dialog was accepted manually. This is recorded as the untrusted counterexample, not as a managed unattended behavior.
3. The floor leg used a PATH shim to the side-by-side 2.1.296 install; the managed launch itself was unchanged. The pane banner confirmed 2.1.296.
4. The original collector-kill event summaries are reconstructed from the `channel.json` stop snapshot because cleanup removed the raw store before the summary command ran; the summary files state this explicitly. The rerun summaries were generated before cleanup.
5. Direct-input packs contain a `not_applicable` admission record because no gateway submission was used.
6. The untrusted scenarios are inspection-only; no provider session was launched, and the pack files say `not_applicable` where a session would normally supply data.

## Cleanup Evidence

Every launched scenario pack has `cleanup.json` with: collector alive after stop `false`, hook subtree present after stop (where a channel existed) and absent after `cleanup session`, session root absent after cleanup, and tmux session absent. The permission-latest pack's cleanup record was written manually after its manual stop/cleanup because the scenario predated the helper; it records the same checks.

The four rerun packs (`compaction-*-rerun/`, `collector-kill-*-rerun/`) record the same cleanup outcome, including the relaunch tmux name where applicable.

Final host checks after all scenarios, including the rerun:

- `tmux ls | grep -Ei 'houmao-smoke|hook-smoke'` returned no campaign sessions.
- `pgrep -af '[h]ook_observation.collector'` returned no collectors.
- The scratch project overlay and evidence remain under `tmp/hook-observation-smoke/`; no `src/`, `tests/`, or OpenSpec files were modified.

## Qualification Verdict

G5 (live provider smoke) is satisfied for normal turn, direct input, permission wait, and stop: the channel installed, delivered events, merged posture correctly, and every session stayed controllable. In the original run, G6 was satisfied for disabled hooks but collector death failed the expected channel-state requirement because the channel stayed `active` until staleness (D2), and G7 compaction outcome preservation failed on both supported versions (D1).

After the `e59b05bd` rerun, the previously failing G6 collector-state check and G7 compaction-outcome check pass at both versions: collector death publishes `stopped` within one or two poll cycles without a TUI change, and compaction preserves the hook-latched `success` outcome and Stop timestamp. D1, D2, and D7 are verified fixed. D6 remains a named gap: v1 has no `untrusted_workspace` producer; the managed launch policy prevents the precondition. Phase 0 opt-in remains appropriate; the rerun removes the earlier default-on blockers.

## No-Product-Change Declaration

This campaign changed no file under `src/`, `tests/`, or `openspec/`. Findings above are reported for a follow-up fix; they were not repaired in the original campaign. The follow-up fix commit `e59b05bd` addressed D1, D2, and D7, and this report records the rerun evidence.
