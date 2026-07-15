# Use Case 02: Pressure-Test Long-Horizon TUI State Tracking

## Actor Goal

As a Houmao developer, I want long-horizon TUI tracking tests with many operations in one session, so that I can detect state leakage, drift, oscillation, duplicated outcomes, lost authority, and downstream contradictions that focused cases cannot expose.

## Use Case

The developer runs five distinct long-horizon sessions against fresh run-local copies of the vendored Boltons project, each with at least 20 recorded user operations. Every session combines several state-transition families while retaining the same provider session, tmux pane, recorder, and tracker, except where restart behavior is the explicit stimulus. Across the five sessions, the plan pressures every in-scope transition family defined by [UC-01](uc-01-qualify-focused-tui-state-transitions.md).

This use case reuses UC-01's unattended launch contract, state-coverage ledger, independent native-TUI labeling method, canonical capture rules, degraded-cadence oracles, and exclusions. It does not redefine detector correctness. A transition must first have a focused `PS-*` or `MS-*` owner in UC-01 before it can count toward long-horizon coverage here.

Every live provider session uses `unattended` mode. An approval, permission, trust, login, update, session-picker, browser, or model-generated user-question prompt is a failed test unless a predeclared intervention allowlist proves that the provider hard-codes the prompt and exposes no supported bypass.

## Relationship to UC-01

UC-01 asks whether one state or bounded transition is classified correctly and normally limits a session to one through four user interactions. UC-02 asks whether those correct transitions remain coherent after at least 20 user operations and accumulated terminal history.

A UC-02 failure must be reduced to the smallest UC-01-style reproduction before detector logic changes whenever accumulated history is not necessary to reproduce the defect. A passing UC-02 session cannot compensate for a missing or failing focused contract.

## Supported Action

### Run Long-Horizon Transition Pressure Sessions

Execute five interaction procedures, each with at least 20 user operations in one maintained provider session.

- context
  - Actor **has** qualified focused transition contracts, stable provider credentials, the pinned vendored Boltons fixture, a run-scoped native TUI, and long-horizon scripts whose operations are individually recorded.
  - System **has** bounded capture storage, transition history, replay sweeps, a confirmation watchdog, downstream-consumer simulation, and cleanup controls.
- intent
  - Actor **wants** confidence that state tracking does not accumulate stale outcomes, oscillate, lose authority, or publish contradictory state over many turns.
  - Actor **wonders** "Will the twentieth operation preserve the same transition semantics and downstream safety as the first?"
- action
  - Actor then **asks** the system to execute ST-01 through ST-05 and evaluate canonical and degraded-cadence replay.
- result
  - Actor **gets** five session reports, 101 correlated scripted operations for one complete ST-01 through ST-05 pass, transition-family coverage, cadence verdicts, transition-growth diagnostics, downstream-consumer traces, and retained failure slices.

## Transition-Family Coverage Obligation

The five sessions must collectively exercise every in-scope UC-01 transition family under accumulated-history pressure:

- startup and prompt-free readiness;
- draft acquisition, editing, clearing, and reacquisition;
- explicit-input and surface-inference authority;
- active turns, temporal-growth inference, steering, and stable completion;
- success invalidation by newer authority;
- interruption, repeated interruption identity, and recovery;
- explicitly opened non-confirmation overlays and conservative unknown state;
- unattended command, read, write, edit, and plan operations;
- stale spinner, interruption, failure, and success evidence in scrollback;
- process loss, turn-anchor loss, restart, and conservative recovery;
- delayed and irregular observation schedules;
- schema-valid downstream admission and terminal-outcome uniqueness.

Provider-visible network and LLM API errors remain excluded because the test cannot induce them reliably. Confirmation-driven states remain forbidden live outcomes under `unattended` mode and retain their synthetic or replay owners from UC-01.

## Boltons Test-Project Contract

Every session runs in a fresh copy of `tests/fixtures/test-projects/boltons`. The vendored fixture is immutable test input; an agent must never work in or modify that source directory.

Before launching the provider, the coordinator:

1. copies the fixture to `<run-root>/projects/<session-id>-<provider>/boltons`;
2. records the source path and imported upstream revision `979fa9b613fa8c0a455ae16ea6f2ec91c11ecafe` from the fixture README;
3. removes generated caches from the copy, then initializes a fresh Git repository;
4. configures a run-local Git identity, stages every copied file, and creates a `houmao-baseline` commit;
5. verifies that `python -m pytest --collect-only -q` works without network access or dependency installation and collects 437 tests for the pinned fixture revision;
6. launches the provider with the copied Boltons root as its working directory.

The session manifest records the absolute copied-project path, baseline commit, Python executable, exact provider launch command, exact tmux pane in a dedicated single-pane window, initial `git status --short` output, and SHA-256 of the vendored fixture tree excluding generated caches. Cleanup may delete only the run-local copy.

All engineering prompts use this literal safety prefix:

`Work only in this Boltons checkout. Do not use the network, install packages, modify dependency files, or ask questions.`

Tables abbreviate that exact prefix as `{{SAFE}}`. Before sending a prompt, the coordinator replaces `{{SAFE}}` with the literal text above and stores the fully expanded text in `input_events.ndjson`. No other prompt substitution is allowed except the declared `{{PLACEHOLDER_LITERAL}}`, `{{PANE}}`, and `{{LAUNCH_COMMAND}}` values. “Submit” means send the complete expanded text followed by `Enter` in one recorded semantic input event. “Type without submitting” sends no `Enter`.

Engineering checkpoints and tracker verdicts are distinct. A file or command checkpoint proves that the scripted project operation occurred; the tracker oracle judges visible state and transition semantics. An unmet engineering checkpoint yields `scenario_task_divergence` and does not become a tracker failure.

## Five Long-Horizon Transition Pressure Sessions

Each numbered row is one recorded user operation. Every provider is launched in the maintained unattended posture. Waits for visible checkpoints, label review, and allowlisted scripted interventions are harness actions and do not count. The provider process, tmux pane, recorder, and tracker remain the same within a session, except that ST-05 deliberately restarts the provider while retaining the copied project, pane, recorder, and tracker.

### ST-01: Boltons Read-Only Draft Editing and Successful Turns

Primary providers: Claude and Codex. Purpose: detect stale-success leakage and editor-classification drift while the agent performs repeated, concrete Boltons inspection tasks. This session must leave the baseline worktree clean.

| Op | Exact prompt or action | Engineering checkpoint | Tracker checkpoint or invariant |
| --- | --- | --- | --- |
| 1 | Type without submitting: `{{SAFE}} Read boltons/iterutils.py and tests/test_iterutils.py. Do not edit files. Report the definition line and test line for pairwise, then end with ST01-A` | No process or file action yet | Editing `yes`; last-turn result `none` |
| 2 | Append the literal nine characters ` WINDOWED` | Draft now ends in `ST01-A WINDOWED` | Editing remains `yes`; no success candidate |
| 3 | Press `Backspace` exactly nine times | Draft returns byte-for-byte to operation 1 | Draft authority remains current; no terminal result |
| 4 | Press `Enter` | Response cites both files, ends with `ST01-A`, and `git status --short` remains empty | Explicit-input authority; active then one success |
| 5 | Type without submitting: `{{SAFE}} Read boltons/strutils.py and tests/test_strutils.py. Do not edit files. Report the definition line of parse_int_list and two existing test inputs. End with ST01-B` | No new file change | Prior success clears; editing `yes` |
| 6 | Press `Left` once | Cursor is immediately before the final `B` | Editing remains `yes` |
| 7 | Type the literal `EDITED-` | Draft ends with `ST01-EDITED-B` | No terminal result is inferred |
| 8 | Press `Enter` | Response ends with `ST01-EDITED-B`; worktree remains clean | Fresh active turn then one success |
| 9 | Type `/` without submitting | Slash menu is visible | Conservative overlay state; no success settlement |
| 10 | Press `Escape` | Slash menu closes and empty editor returns | Ready posture returns without a new outcome |
| 11 | Type without submitting: `{{SAFE}} Read boltons/urlutils.py only. Do not edit files. Name the URL class and the find_all_links function. End with ST01-C` | No file change | Editing `yes` with fresh authority |
| 12 | Press `Ctrl+U` | Editor is empty | Ready/non-editing; no fabricated result |
| 13 | Retype operation 11 exactly | Draft matches operation 11 byte-for-byte | Editing authority is reacquired |
| 14 | Press `Enter` | Response ends with `ST01-C`; worktree remains clean | Active then one success |
| 15 | Type without submitting: `{{SAFE}} Read boltons/fileutils.py and tests/test_fileutils.py. Do not edit files. State the default keep value of rotate_file and end with ST01-D` | No file change | Prior success clears |
| 16 | Send `Space Space Backspace Backspace` as one recorded key sequence | Draft text is unchanged | State family does not oscillate |
| 17 | Press `Enter` | Response reports `keep=5`, ends with `ST01-D`, and worktree remains clean | Active then one success |
| 18 | Type without submitting: `{{SAFE}} Read pyproject.toml only. Do not edit files. Reply exactly ST01-E PYTHON>=3.7` | No file change | Prior success clears; editing `yes` |
| 19 | Press `Enter` | Visible response contains exactly `ST01-E PYTHON>=3.7` as its substantive answer | Fifth active turn settles once |
| 20 | Press `Escape` once at the empty ready editor | No project change | Final success remains current; no new authority or outcome |

### ST-02: Boltons Interruption, Steering, Recovery, and Re-Interruption

Primary provider: Codex, mirrored on Claude where steering is supported. Purpose: exercise repeated interruption identity and active-draft overlap during long read-only repository analysis. The coordinator sends steering or interrupt keys immediately after the required active checkpoint rather than waiting for task completion.

| Op | Exact prompt or action | Engineering checkpoint | Tracker checkpoint or invariant |
| --- | --- | --- | --- |
| 1 | Submit: `{{SAFE}} Read boltons/iterutils.py, boltons/dictutils.py, boltons/urlutils.py, and their matching test files. Do not edit files. Produce at least 40 numbered bullets, each naming one public symbol, its definition line, and one tested behavior. End with ST02-A` | Agent begins multi-file inspection; worktree remains clean | Active turn 1 |
| 2 | While turn 1 is active, type without submitting: `Steer: cover iterutils.py first and put pairwise, windowed, and backoff in the first three bullets.` | Steering draft is visible | Active plus editing when supported |
| 3 | Press `Enter` | Steer text is accepted | Steer handoff remains active; no terminal result |
| 4 | After one post-steer active frame, press `Ctrl+C` once | Worktree remains clean | Interrupted result 1; exactly one terminal interruption |
| 5 | Type without submitting: `{{SAFE}} Re-read boltons/iterutils.py and tests/test_iterutils.py. Do not edit files. Produce 30 numbered behavior examples for pairwise, windowed, and backoff. End with ST02-RECOVERY-A` | No file change | Interruption clears under fresh draft authority |
| 6 | Press `Enter` | Multi-file read begins | Active turn 2 |
| 7 | After the first visible response line while still active, press `Ctrl+C` once | Worktree remains clean | Interrupted result 2, distinct from result 1 |
| 8 | Type without submitting: `{{SAFE}} Read pyproject.toml only. Do not edit files. Reply exactly ST02-B PYTHON>=3.7` | No file change | Fresh draft authority |
| 9 | Press `Enter` and wait for ready | Response contains `ST02-B PYTHON>=3.7` | Active then success 1 |
| 10 | Submit: `{{SAFE}} Read every Python module directly under boltons/ and every test_*.py file directly under tests/. Do not edit files. Produce a module-to-test coverage table with at least 35 rows and end with ST02-C` | Broad read-only traversal begins | Prior success clears; active turn 4 |
| 11 | While turn 4 is active, type without submitting: `Steer: sort the coverage table alphabetically and include cacheutils.py, iterutils.py, strutils.py, and urlutils.py first.` | Steering draft is visible | Active/editing overlap |
| 12 | Press `Ctrl+U` | Steering editor becomes empty | Active continues; no completion |
| 13 | Type without submitting: `Steer: instead group the table into data structures, iteration, text, files, time, and networking.` | Replacement steering draft is visible | Editing returns without new terminal state |
| 14 | Press `Enter` | Replacement steer is accepted | Active handoff |
| 15 | After one post-steer active frame, press `Ctrl+C` once | Worktree remains clean | Interrupted result 3; no duplicate outcome |
| 16 | Type `/` without submitting | Slash menu appears | Overlay does not revive interruption as activity |
| 17 | Press `Escape` | Slash menu closes | Ready/interrupted posture remains coherent |
| 18 | Type without submitting: `{{SAFE}} Read README.md and CHANGELOG.md only. Do not edit files. Reply with the current package name and end with ST02-RECOVERED` | No file change | Interrupted result clears |
| 19 | Press `Enter` and wait for ready | Response ends with `ST02-RECOVERED`; worktree remains clean | Active then success 2 |
| 20 | Type without submitting: `{{SAFE}} Read boltons/cacheutils.py next, but do not start until I submit this draft.` | No tool starts and no file changes | Final state is editing `yes` with no extra outcome |

If operations 1, 6, or 10 complete before the scheduled steering or interrupt checkpoint, the attempt is `stimulus_too_short` and must be rerun. The coordinator must not invent a replacement prompt during the live session.

### ST-03: Concrete Unattended Boltons Tool and Edit Workflow

Primary provider: Kimi, with Claude and Codex variants. Purpose: exercise read, command, write, edit, plan, test, and diff operations without confirmation. Every mutation stays inside the run-local Boltons copy.

| Op | Exact submitted prompt | Required engineering checkpoint | Tracker checkpoint or invariant |
| --- | --- | --- | --- |
| 1 | `{{SAFE}} Use terminal tools now. Run pwd and git status --short. Do not edit files. Reply with the working-directory basename, the status output, and ST03-01.` | Basename is `boltons`; status is empty | Active then success without confirmation |
| 2 | `{{SAFE}} Read pairwise and windowed in boltons/iterutils.py and their tests in tests/test_iterutils.py. Do not edit files. Report their definition and test line numbers, then end with ST03-02.` | Both source and test files are read; status remains empty | Fresh active turn and one success |
| 3 | `{{SAFE}} Create tests/test_houmao_long_horizon.py. It must import pairwise from boltons.iterutils and define test_pairwise_contract asserting pairwise([1, 2, 3]) == [(1, 2), (2, 3)]. Modify no other file. End with ST03-03.` | New file exists with one import and one test | Write is unattended; active then success |
| 4 | `{{SAFE}} Run python -m pytest -q tests/test_houmao_long_horizon.py. Do not edit files. Report the pass count and end with ST03-04.` | Command exits zero with one passing test | Command remains active until one success |
| 5 | `{{SAFE}} Edit only tests/test_houmao_long_horizon.py. Add windowed to the boltons.iterutils import and add test_windowed_contract asserting windowed([1, 2, 3, 4], 3) == [(1, 2, 3), (2, 3, 4)]. End with ST03-05.` | File contains two named tests | Edit completes without confirmation |
| 6 | `{{SAFE}} Run python -m pytest -q tests/test_houmao_long_horizon.py. Do not edit files. Report the pass count and end with ST03-06.` | Command exits zero with two passing tests | Fresh command turn; one success |
| 7 | `{{SAFE}} Read parse_int_list in boltons/strutils.py and its existing tests in tests/test_strutils.py. Do not edit files. Report one ascending and one descending range example, then end with ST03-07.` | Both files are read; test file unchanged | Read completes without blocked state |
| 8 | `{{SAFE}} Edit only tests/test_houmao_long_horizon.py. Import parse_int_list from boltons.strutils and add test_parse_int_list_contract asserting parse_int_list('3,1,5-7') == [1, 3, 5, 6, 7]. End with ST03-08.` | File contains three named tests | Edit is unattended and settles once |
| 9 | `{{SAFE}} Run python -m pytest -q tests/test_houmao_long_horizon.py. Do not edit files. Report the pass count and end with ST03-09.` | Command exits zero with three passing tests | No stale blocked or prior result |
| 10 | `{{SAFE}} Read find_all_links in boltons/urlutils.py and its tests in tests/test_urlutils.py. Do not edit files. Report its with_text option and end with ST03-10.` | Source and tests are read | Read turn settles once |
| 11 | `{{SAFE}} Edit only tests/test_houmao_long_horizon.py. Import find_all_links from boltons.urlutils and add test_find_all_links_contract asserting [str(url) for url in find_all_links('see https://example.com/a')] == ['https://example.com/a']. End with ST03-11.` | File contains four named tests | Edit completes without confirmation |
| 12 | `{{SAFE}} Run python -m pytest -q tests/test_houmao_long_horizon.py. Do not edit files. Report the pass count and end with ST03-12.` | Command exits zero with four passing tests | Active then one success |
| 13 | `{{SAFE}} Create docs/houmao-long-horizon.rst with exactly seven lines in this order: 'Houmao Long-Horizon Notes', '=========================', one blank line, '* pairwise: adjacent pairs', '* windowed: sliding tuples', '* parse_int_list: integer ranges', and '* find_all_links: URL discovery'. Modify no other file. End with ST03-13.` | Documentation file has the exact seven requested lines | Write completes unattended |
| 14 | `{{SAFE}} Run sha256sum docs/houmao-long-horizon.rst. Do not edit files. Reply with the 64-character digest and ST03-14.` | Visible digest matches the file | Command turn has one terminal outcome |
| 15 | `{{SAFE}} Edit only docs/houmao-long-horizon.rst. Append a blank line and the exact line 'Validation command: python -m pytest -q tests/test_houmao_long_horizon.py'. End with ST03-15.` | Exact validation line is present once | Edit completes without confirmation |
| 16 | `{{SAFE}} Run python -m pytest -q tests/test_houmao_long_horizon.py tests/test_iterutils.py tests/test_strutils.py tests/test_urlutils.py. Do not edit files. Report the exit status and pass count, then end with ST03-16.` | Command exits zero | Long command remains active until one success |
| 17 | `{{SAFE}} Run git status --short and read tests/test_houmao_long_horizon.py and docs/houmao-long-horizon.rst. Do not edit files. In chat, give exactly three plan steps for adding a pairwise end-value test, then end with ST03-17.` | Status shows only the two declared untracked files; no change occurs during planning | Plan response requires no approval or user answer |
| 18 | `{{SAFE}} Apply the plan by editing only tests/test_houmao_long_horizon.py. Add test_pairwise_end_contract asserting pairwise([1], end=None) == [(1, None)]. End with ST03-18.` | Test file contains five named tests | Planned edit completes unattended |
| 19 | `{{SAFE}} Run git diff --no-index /dev/null tests/test_houmao_long_horizon.py and git diff --no-index /dev/null docs/houmao-long-horizon.rst. Exit status 1 is expected because both files are new. Summarize only the two paths and five test names. Do not edit files. End with ST03-19.` | Both no-index diffs show only the declared files | Read/diff turn receives fresh authority |
| 20 | `{{SAFE}} Run python -m pytest -q tests/test_houmao_long_horizon.py and git status --short. Do not edit files. Report five passing tests, both changed paths, and ST03-20.` | Five tests pass; status lists only the declared new files | Final ready/success with zero interventions |

### ST-04: Boltons UI Overlays, Resize, and Stale Scrollback

Providers: run once for each of Claude, Codex, and Kimi. Purpose: stress editor classification, explicitly opened navigation overlays, terminal geometry, and visible-region precedence around concrete read-only Boltons tasks.

The scenario manifest resolves `{{PLACEHOLDER_LITERAL}}` before recording:

| Provider | Exact `{{PLACEHOLDER_LITERAL}}` |
| --- | --- |
| Claude | `Try "fix typecheck errors"` |
| Codex | `Find and fix a bug in @filename` |
| Kimi | `type a message or use /help for commands.` |

The manifest also replaces `{{PANE}}` with the exact owned tmux target. Resize and copy-mode commands are run by the coordinator and recorded as semantic terminal-control events.

| Op | Exact prompt or action | Engineering checkpoint | Tracker checkpoint or invariant |
| --- | --- | --- | --- |
| 1 | Type `/` without submitting | Slash menu is visible | Unknown/overlay, never success |
| 2 | Press `Down` once | Selection moves down once | Overlay remains bounded |
| 3 | Press `Up` once | Selection returns | No turn result change |
| 4 | Press `Escape` | Slash menu closes | Ready returns |
| 5 | Type `{{PLACEHOLDER_LITERAL}}` without submitting | Literal appears as user-entered editor text | Editing `yes`, not provider placeholder |
| 6 | Press `Ctrl+U` | Editor becomes empty | Ready/non-editing |
| 7 | Run `tmux resize-window -t {{PANE}} -x 72 -y 24` | Pane is exactly 72 columns by 24 rows | Wrapping does not fabricate activity or interruption |
| 8 | Type without submitting: `{{SAFE}} Read README.md only. Do not edit files. Reply with the upstream URL in the Houmao Vendored Test Fixture section and end with ST04-A` | Draft is visible in narrow pane | Editing authority survives wrapping |
| 9 | Press `Enter` and wait for ready | Response includes `https://github.com/mahmoud/boltons` and `ST04-A` | Active then one success |
| 10 | Run `tmux copy-mode -t {{PANE}}` followed by `tmux send-keys -t {{PANE}} -X page-up` as one control event | Visible pane shows older scrollback | Tracker remains conservative about copied scrollback |
| 11 | Run `tmux send-keys -t {{PANE}} -X cancel` | Current provider surface returns | Current visible region regains precedence |
| 12 | Run `tmux resize-window -t {{PANE}} -x 120 -y 36` | Pane is exactly 120 by 36 | State remains coherent after reflow |
| 13 | Send the key sequence `/model Enter` as one navigation event | Provider model selector opens | Modal/unknown posture; no requested intervention |
| 14 | Press `Down` once | Selector highlight moves once | No terminal outcome |
| 15 | Press `Escape` | Selector closes without changing model | Ready returns |
| 16 | Submit: `{{SAFE}} Read boltons/cacheutils.py, boltons/dictutils.py, boltons/iterutils.py, boltons/strutils.py, and their matching tests. Do not edit files. Produce 30 numbered bullets comparing their public APIs and end with ST04-B.` | Broad read-only inspection begins | Active turn; prior success cleared |
| 17 | After the first visible response line while active, press `Ctrl+C` once | Worktree remains clean | One interrupted outcome |
| 18 | Run `tmux resize-window -t {{PANE}} -x 88 -y 28` | Pane is exactly 88 by 28 while interruption evidence remains | Interruption survives reflow without duplication |
| 19 | Type without submitting: `{{SAFE}} Read pyproject.toml only. Do not edit files. Reply exactly ST04-RECOVERED` | Recovery draft is visible | Stale interruption clears |
| 20 | Press `Enter` and wait for ready | Response contains `ST04-RECOVERED`; worktree remains clean | Active then one success; stale scrollback does not contaminate it |

After operation 13 opens the model selector and before operation 14 moves the highlight, the harness performs an uncounted hold longer than the configured shortened unknown timeout. The tracker must evolve from conservative unknown to its documented stalled posture without manufacturing completion, blockage, or a request for confirmation. Operation 14 then proves that the explicitly opened navigation surface remains usable, and operation 15 must recover to ready.

If `/model Enter` does not open a cancelable selector for a maintained provider version, preflight marks that provider variant `unsupported_navigation_surface`. The coordinator must not discover and substitute a different command during recording.

### ST-05: Mixed Boltons Session with Downstream Consumption and Restart

Providers: Codex and Kimi in maintained unattended posture. Purpose: combine ordinary turns, overlays, unattended tools, steering, interruption, process loss, restart, and downstream state consumption in one copied Boltons project.

The manifest resolves `{{LAUNCH_COMMAND}}` to the exact unattended launch command used initially. The maintained Codex and Kimi variants use `Ctrl+D` at an empty ready editor to exit. Preflight must prove that behavior; no fallback exit action may be invented during recording.

| Op | Exact prompt or action | Engineering checkpoint | Tracker checkpoint or invariant |
| --- | --- | --- | --- |
| 1 | Submit: `{{SAFE}} Read README.md only. Do not edit files. Reply exactly ST05-A BOLTONS` | Worktree remains clean | Active then success |
| 2 | Type without submitting: `{{SAFE}} Read pyproject.toml and report the minimum Python version. End with ST05-B` | Draft visible; no tools started yet | Success clears under new draft authority |
| 3 | Press `Enter` and wait for ready | Response includes `>=3.7` and `ST05-B` | Active then one success |
| 4 | Submit: `{{SAFE}} Read every Python file directly under boltons/ and produce at least 35 numbered bullets mapping modules to representative public symbols. Do not edit files. End with ST05-C` | Broad read-only traversal begins | Active turn |
| 5 | After the first visible response line while active, press `Ctrl+C` once | Worktree remains clean | One interrupted outcome |
| 6 | Type without submitting: `{{SAFE}} Run git status --short. Do not edit files. Reply exactly ST05-D CLEAN if the output is empty.` | Recovery draft visible | Interruption clears |
| 7 | Press `Enter` and wait for ready | Response contains `ST05-D CLEAN` | Active then success |
| 8 | Type `/` without submitting | Slash menu appears | Unknown/modal without outcome |
| 9 | Press `Escape` | Slash menu closes | Ready returns |
| 10 | Submit: `{{SAFE}} Use terminal tools now. Create houmao_artifacts/st05.txt with exactly the line 'boltons long horizon state'. Modify no other file. End with ST05-E.` | File exists with exact one-line content | Tool turn completes without confirmation |
| 11 | Submit: `{{SAFE}} Read houmao_artifacts/st05.txt and run sha256sum on it. Do not edit files. Reply with its exact content, the digest, and ST05-E-READ.` | Visible content and digest match file | Fresh active turn; one success |
| 12 | Submit: `{{SAFE}} Read boltons/fileutils.py, boltons/iterutils.py, boltons/strutils.py, and their tests. Do not edit files. Produce 25 numbered comparison bullets and end with ST05-F.` | Long read-only analysis begins | Active turn with fresh authority |
| 13 | While operation 12 is active, type without submitting: `Steer: put atomic_save, pairwise, windowed, parse_int_list, and human_readable_list in the first five bullets.` | Steering draft visible | Active/editing overlap where supported |
| 14 | Press `Enter` and wait for final ready | Steer is accepted; no files change | Still active, then exactly one success |
| 15 | Type without submitting: `{{SAFE}} Run python -m pytest -q tests/test_fileutils.py tests/test_iterutils.py tests/test_strutils.py. Report the exit status and end with ST05-G.` | Draft visible; tests not started yet | Prior success clears |
| 16 | Press `Ctrl+U` | Editor becomes empty | Ready/non-editing; no terminal outcome |
| 17 | Retype operation 15 exactly | Draft restored byte-for-byte | Editing authority reacquired |
| 18 | Press `Enter` and wait for ready | Targeted tests exit zero and response ends `ST05-G` | Active then one success |
| 19 | At the empty ready editor, press `Ctrl+D` once | Provider exits to the owned shell; copied project remains | `tui_down`; old turn anchor absent or lost; no stale admission |
| 20 | At the shell prompt, send expanded `{{LAUNCH_COMMAND}}` followed by `Enter` | Same provider restarts in same pane and working directory without a prompt | Conservative startup/unknown then ready; old success not resurrected |
| 21 | Submit: `{{SAFE}} Read houmao_artifacts/st05.txt. Do not edit files. Reply exactly ST05-H boltons long horizon state` | Restarted process reads the pre-restart artifact | Fresh authority, active, then one success |

After operation 21, the harness performs an uncounted stability wait of `settle_seconds + 2 × observed_sample_interval`. The final state must be stable ready/success, and `git status --short` must list only `?? houmao_artifacts/`.


## Capture and Replay Requirements

Use UC-01's canonical capture and replay schedule for every ST session:

1. Verify the maintained unattended posture and arm the confirmation watchdog.
2. Record the independent native TUI at a requested `0.05` second interval, approximately 20 fps, with actual timestamps as authority.
3. Label the visible recording without exposing tracker predictions.
4. Run strict sample-aligned replay on the canonical stream.
5. Run fixed 10 Hz, 5 Hz, and 2 Hz streams with zero and half-interval phase offsets.
6. Run seeded jitter and isolated-gap variants when the derivation interface supports them.
7. Run one bursty schedule per session: five fast samples near an operation, followed by one sample after `0.5s`, repeated with a fixed seed.
8. Persist the source-sample mapping for every derived sample.

A delayed replay may omit a short-lived state, but it must remain safe and semantically coherent under UC-01's degraded-cadence invariants. It must not fabricate a terminal result, reverse active and terminal order, retain stale submit-safe readiness across liveness loss, or associate one turn's outcome with another turn.

## Acceptance Criteria

This use case passes as a group only when:

- all five sessions execute their full catalogs: 20 operations each for ST-01 through ST-04 and 21 for ST-05, for 101 operations total;
- every operation has a unique event id, timestamp, semantic action, and expected checkpoint;
- every session uses a fresh run-local copy of the pinned Boltons fixture and records its source hash, baseline commit, expanded prompts, exact control actions, and final diff;
- the vendored source tree remains byte-for-byte unchanged, excluding ignored caches that the preflight forbids or removes;
- every expanded engineering prompt matches the procedure exactly; the coordinator sends no ad hoc recovery, replacement, or clarification prompt;
- no provider accesses the network, installs a package, or modifies `pyproject.toml`, `setup.cfg`, `tox.ini`, or another dependency/configuration file;
- every engineering checkpoint passes, or the attempt is reported separately as `scenario_task_divergence` and excluded from tracker qualification;
- ST-01, ST-02, and ST-04 finish with a clean copied worktree; ST-03 changes only `tests/test_houmao_long_horizon.py` and `docs/houmao-long-horizon.rst`; ST-05 adds only `houmao_artifacts/st05.txt`;
- the five sessions collectively cover every in-scope transition family listed above;
- canonical replay has zero unexplained public-state mismatches;
- every fixed-rate replay at 2 Hz or faster has zero safety-invariant violations;
- every provider launch resolves an unattended strategy and passes its prompt-free readiness check;
- no session shows an unallowlisted confirmation, approval, permission, trust, login, update, session-picker, browser, or user-question prompt;
- any allowlisted hard-coded intervention is scripted, excluded from the user-operation count, and reported as `pass_with_unavoidable_intervention`;
- every terminal outcome belongs to the correct turn and newer authority clears stale outcomes;
- no session leaks a stale blocked state, interruption, failure, success, or active reason into an unrelated later turn;
- the tracker and downstream consumer remain live without unbounded transition growth, deadlock, or uncaught exception;
- final tracker state, cleanup state, and retained artifact inventory agree;
- failures retain a minimal slice spanning the preceding operation, first divergence, and following stabilization point.

## Main Flow

1. The developer confirms that UC-01 provides a focused owner for every transition family selected for pressure testing.
2. The coordinator resolves maintained provider versions and unattended launch strategies.
3. The coordinator verifies the pinned Boltons fixture revision and source hash, copies it to the run root, removes caches, initializes Git, and creates the `houmao-baseline` commit.
4. The coordinator runs the 437-test collection preflight without network access or dependency installation and records the exact Python executable.
5. The coordinator prepares an isolated provider home and writes `unattended-posture.json`.
6. The operator launches the ordinary provider TUI in the copied Boltons root without Houmao role prompts, skills, bootstrap messages, or tracker feedback.
7. The coordinator verifies prompt-free readiness, exact exit/navigation actions where required, and starts the confirmation watchdog.
8. The recorder starts at approximately 20 fps.
9. The coordinator expands only the declared prompt tokens, executes one ST procedure, and records every expanded prompt, key sequence, pane-control action, and checkpoint as a semantic input event.
10. The operator labels the recording without seeing tracker output.
11. The harness validates the declared project checkpoints and final diff independently from the tracker verdict.
12. The harness replays canonical and degraded schedules through the shared tracker.
13. A simulated downstream consumer checks schema validity, admission safety, transition monotonicity, and terminal-outcome uniqueness.
14. The coordinator repeats the flow for all five procedures, checks aggregate transition-family coverage, verifies that the vendored fixture is unchanged, preserves failure slices, and cleans up only owned resources.

## Alternative and Exception Flows

- If a session crashes before its twentieth operation, mark it incomplete and rerun it from a fresh provider process.
- If the vendored fixture revision, source hash, or 437-test collection checkpoint differs, stop before launch with `fixture_preflight_failed`.
- If an agent works in the vendored source tree, accesses the network, installs a dependency, or modifies a forbidden project file, stop with `unsafe_mutation_scope` and retain the operation that caused it.
- If an exact engineering checkpoint fails while state tracking remains coherent, report `scenario_task_divergence`; do not label it as a tracker defect and do not send an improvised corrective prompt.
- If a scheduled interruption target settles before the interrupt or steering action, report `stimulus_too_short` and rerun the unchanged procedure from a fresh copied project.
- If the exact `/model` or `Ctrl+D` action is unsupported during preflight, mark that provider variant unsupported for the procedure; do not substitute another action during recording.
- If the launch-policy registry has no compatible unattended strategy, stop with `unsupported_unattended_version`; do not fall back to `as_is`.
- If an unallowlisted intervention prompt appears, stop normal operations, retain the evidence slice, and fail `unattended_confirmation_violation`.
- If a prompt matches a predeclared allowlist entry, send only its declared scripted response and use `pass_with_unavoidable_intervention` at best.
- If a network or LLM API error occurs accidentally, quarantine that span from required coverage. Continue only if state authority remains clear.
- If the recorder misses the complete span for a required transition, rerun the session; do not reconstruct ground truth from tracker output.
- If a failure reproduces in fewer than five user interactions, add or update its focused UC-01 case and link the long-horizon failure slice to it.
- If cleanup could mutate a pre-existing tmux session, credential bundle, provider home, or working tree, stop with `unsafe_mutation_scope`.

## Mermaid Flow Diagram

```mermaid
flowchart LR
  Focused[UC-01 focused contracts]
  Project([Copy and baseline Boltons])
  Preflight([Verify unattended posture])
  Capture([Record at 20 fps])
  Operations([Run 20 or more operations])
  Labels([Author independent labels])
  Replay([Replay canonical and delayed schedules])
  Consumer([Check downstream state])
  Aggregate([Check five-session coverage])

  Focused --> Project --> Preflight --> Capture --> Operations --> Labels --> Replay --> Consumer --> Aggregate
```

## Durable Outputs

- `sessions/<st-id>/scenario.json`: provider, version, operation script, checkpoints, transition-family map, capture plan, and mutation scope.
- `sessions/<st-id>/project-manifest.json`: vendored source path/revision/hash, copied-project path, Python executable, baseline commit, collection count, allowed final paths, and cleanup owner.
- `sessions/<st-id>/expanded-operations.ndjson`: literal prompts after token expansion, exact key sequences, pane-control commands, checkpoint triggers, and input event ids.
- `sessions/<st-id>/project-final.diff` and `project-final-status.txt`: final changes relative to `houmao-baseline` and the engineering-checkpoint verdict.
- `sessions/<st-id>/recording/`: manifest, cast, pane snapshots, input events, and independent labels.
- `sessions/<st-id>/sweeps/<variant>/`: derived snapshots, source mapping, transition timeline, invariants, and verdict.
- `stress/stress-summary.json`: operation counts, transition-family coverage, provider versions, terminal outcomes, cadence verdicts, and resource usage.
- `stress/downstream-consumer-trace.ndjson`: consumed states, admission decisions, schema results, and monotonic transition indices.
- `confirmation-violations.ndjson`: detected intervention surfaces, allowlist results, evidence frames, and verdicts.
- `issues/<st-id>-<first-divergence>.md`: minimal evidence slice plus the linked or proposed UC-01 focused reproduction.
- `summary_report.md`: aggregate pressure results, coverage gaps, exclusions, and release recommendation.

## Example Prompt and Expected AI Response

### Event 001: Execute the Long-Horizon Suite

> Time: `2026-07-11T15:00:00Z` · Session: `tui-tracker-long-horizon-plan`

User Prompt:

> Use only unattended TUI mode. For each ST procedure, copy `tests/fixtures/test-projects/boltons` to a fresh run-local project, create the `houmao-baseline` commit, and execute the exact prompts and actions in this use case. Run ST-01 through ST-05 with at least 20 recorded user operations each. Record at 20 fps and judge canonical, 10 Hz, 5 Hz, and 2 Hz replay. Do not access the network, install packages, improvise prompts, or answer an avoidable confirmation.

AI:

> The agent should show the focused-contract mapping, Boltons source revision and hash, copied-project paths, baseline commits, 437-test collection results, provider versions, unattended strategy ids, exact tmux targets, expanded operation hashes, operation counts, and intervention allowlist before execution. It should preserve one provider session, pane, recorder, tracker, and copied project through each procedure unless restart is the stated stimulus. It should report engineering-checkpoint and tracker verdicts separately and enforce the aggregate transition-family gate across all five sessions.

## Assumptions and Open Questions

- The recorder can sustain a requested 20 fps on the qualification host; actual timestamps remain authoritative.
- The replay interface supports fixed cadence and phase offsets. Jitter, gap, and bursty schedules may remain `not_run_capability_missing` until schedule-driven derivation exists.
- Provider-neutral semantic operations require provider-specific key sequences.
- The pinned Boltons revision collects 437 tests in the current managed Python environment; a different count is a preflight failure until the fixture or environment expectation is intentionally revised.
- The exact ST-03 assertions and its four-file targeted command were validated against the pinned fixture; the existing targeted files currently pass 192 tests.
- Maintained Codex and Kimi versions must prove the specified empty-editor `Ctrl+D` exit during preflight, and every maintained ST-04 provider must prove the specified `/model` selector before recording.
- Resource thresholds for replay duration, transition-history size, and memory growth should be fixed after one baseline run on the qualification host.
