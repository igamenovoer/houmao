# Test Report: Kimi Native System-Prompt Smoke (Live, 2026-08-09)

- **Change under test**: `openspec/changes/use-kimi-native-system-prompt` (native `$KIMI_CODE_HOME/SYSTEM.md` role-prompt delivery, Kimi >= 0.34.0)
- **Executing change**: `openspec/changes/add-kimi-native-prompt-smoke-test`
- **Environment**: Linux dev box, `kimi` 0.34.0 (`/home/huangzhe/.kimi-code/bin/kimi`), Houmao from this checkout (pixi env), auto credentials imported from the native Kimi Code home via `houmao-mgr project credentials kimi add --code-home ~/.kimi-code`
- **Run root / evidence**: `tmp/kimi-native-prompt-smoke/run-20260809T123938Z/` (evidence bundle in `evidence/`, command log in `logs/commands.log`)

## What Was Tested

The smoke proves that the composed Houmao role prompt reaches a real Kimi Code 0.34.0 agent through the native `SYSTEM.md` contract, on both maintained launch surfaces, using the same auto credential an operator's real Kimi install uses. Verification is two-layered: the artifact layer (provider-native evidence, checked before any prompt submission) is the primary oracle; the behavior layer (a chat probe) is only a secondary confirmation. A frozen-marker role (`KNS-BF999758`) makes the behavior check a token-presence match rather than a wording judgment.

| Leg | What it exercises |
| --- | --- |
| Preflight | `kimi` >= 0.34.0, native-home auto credential posture (`kimi provider list --json`, no secrets read), writable run root |
| Credential import | Auto credential lane (`--code-home` import of the native Kimi home) into a scratch Houmao project |
| Brain build | Specialist creation binding the frozen-marker role to the imported credential |
| Headless | Managed launch, artifact verification, one paid probe turn |
| TUI | Unattended managed TUI launch, 20 Hz `tools.terminal_record` recording, artifact verification, probe through the managed prompt path, blind labeling of the frozen timeline by a subagent |
| Relaunch | Supported managed relaunch with pre/post `SYSTEM.md` digest comparison (no third paid turn) |

## Results: All Pass

`evidence/summary.json` — overall **pass**:

- ✓ preflight (kimi 0.34.0, provider `managed:kimi-code` configured)
- ✓ credential imported from native home
- ✓ headless artifact layer
- ✓ headless behavior layer
- ✓ TUI artifact layer
- ✓ TUI behavior layer
- ✓ no role-bootstrap chat turn (headless)
- ✓ no role-bootstrap chat turn (TUI, blind-labeled)
- ✓ relaunch digest persistence

## Why I Believe the Pass Is Real

The artifact layer does not trust any chat output. For each launch it reads the session manifest (`identity.manifest_path` from `agents single state`) and cross-checks three independent sources against each other:

1. **Manifest launch verification** (`launch_plan.metadata.native_system_prompt`) records `method: native_home_system_prompt`, `validation: passed`, `base_prompt_preserved: true`, `engine_env: KIMI_CODE_LEGACY_FLAG=0`, plus effective and rendered SHA-256 digests.
2. **Bytes on disk**: the managed `SYSTEM.md` starts with the canonical `${base_prompt}\n\n` prefix, its effective suffix contains the frozen marker, and permissions are exactly 0600.
3. **Recomputed digests**: SHA-256 over the on-disk file and over the effective prompt (minus the renderer's single trailing newline, verified against `src/houmao/agents/kimi_system_prompt.py`) match the manifest values exactly — so the file Kimi reads is the file Houmao verified, with no drift between construction and provider start.

The behavior layer then confirms Kimi actually consumed the prompt. Headless stdout (`stream-json`) contains the assistant message `KNS-BF999758 — I am the smoke-test sentinel for the Houmao Kimi native-prompt qualification.` The marker is a random per-run token that exists nowhere except inside the projected effective prompt, so its verbatim presence in the response cannot come from workspace files, user input, or prior sessions.

The TUI leg adds two independent witnesses. The 20 Hz frozen recording (`pane_snapshots.ndjson`, 272 samples, sha256 `23dc0333…`) was blind-labeled by a subagent that never saw tracker output: the timeline shows trust-modal → ready-idle → prompt-in-composer → turn-active → settled-success, with **no role-bootstrap chat turn before the first ready state** — the first chat turn in the transcript is the probe itself. The relaunch leg re-ran the full artifact verification after a managed relaunch and found byte-identical digests with fresh provider-start verification metadata.

## Product Findings From Live Testing

1. **Fixed: `sh -lc` pane wrapper broke every tmux-backed turn on dash systems.** `/bin/sh` is dash on this machine; dash as a login shell aborts on bash syntax in `/etc/profile.d/bash_completion.sh`, so the `respawn-pane` command died instantly and `turn submit` hung forever. Root-caused by reproducing `respawn-pane` with a scratch tmux session. Fixed by switching to `bash -lc` in `src/houmao/agents/realm_controller/backends/headless_runner.py` (2 sites) and `local_interactive.py` (1 site), with the test pane simulators updated to match. Evidence the fix is right: the pre-existing `tests/unit/agents/realm_controller/test_headless_runner.py` failed on this machine before the fix (5-minute timeout per case) and passes after (11/11 in 1.5 s); the full `tests/unit/agents/realm_controller` suite passes (635 tests); ruff format and lint are clean on the touched files.
2. **Deferred: fresh managed homes trigger Kimi's "Trust this folder?" modal.** A new brain home has no workspace-trust record for the launch workdir, so the Kimi TUI opens a modal that swallows pasted prompts. The smoke script detects and accepts it once and records the intervention in evidence (consistent with the corpus spec's labeled-intervention contract). Whether Houmao should pre-seed trust for launch workdirs is a product decision noted in the change's `design.md`.

## Caveats

- The legs were executed individually during iterative debugging (same run id, same specialist and credential); `scripts/run_all.sh` encodes the full pipeline but has not itself been invoked end-to-end as a single command.
- TUI prompt submission showed a ~20–30 s lag from paste to visible processing on first turn (session creation on first message); relevant when planning the 5.3 corpus recording cadence.
- Scope was the smoke subset: NSP-002 placeholder rejection and NSP-003 stale-removal remain covered only by hermetic unit tests, and the full recorded-corpus qualification (parent change tasks 5.3–5.4) is still open.
