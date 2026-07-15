# UC-05 Pending-Input Replay Qualification

## Result

The maintained Claude Code, Codex CLI, and Kimi Code profiles passed the manually audited UC-05 replay qualification. Across 3,634 canonical source samples, `surface_pending_input` produced no mismatches against the independent human labels. All eighteen lower-frequency or irregular replay variants also produced no mismatches and no cadence-induced `yes → no → yes` oscillation. Three Codex variants skipped the isolated one-frame pre-queue `no` checkpoint, which is meaningful undersampling rather than a detector failure.

The one/two/three-pending engineering matrix also confirmed that queue depth does not leak into the public field. The tracker reports presence as `yes` or `no` after classification, with `unknown` reserved for incomplete startup or ambiguous surfaces. Claude visibly caps its queue at one item. Kimi's three-item run remains tainted by an unrelated non-fatal active-pattern timeout.

## Scope and Method

This report qualifies only the new public `surface_pending_input` field. Human review used the existing pane-plus-pattern-label videos to identify structural queue boundaries, then persisted a separate pending-input oracle. The current analyzer never supplied the manual labels.

The recorder manifests requested a 0.05-second interval (20 fps). Capture-pane and serialization overhead yielded median observed intervals of 0.104579 to 0.109569 seconds, so the frozen streams are 20 fps requests rather than actual 20 fps observations. Derived schedules use recorder timestamps. The 10 Hz variants consequently retain nearly every source sample.

## Frozen Canonical Recordings

| Provider | Observed version and selected profile | Recording root | Samples | SHA-256 of `pane_snapshots.ndjson` | Requested interval | Taint |
|---|---|---|---:|---|---:|---|
| Claude Code | Pane header `2.1.209`; maintained `2.1.x` profile | `tmp/houmao-dev-testing/20260714-claude-pending-v2/claude-attempt-001/capture/recording` | 1,546 | `46feaab5ea8ac6a94182287f21a2f67c52a9db80ffa1ecc5f1cc36730306ff9f` | 0.05 s | none |
| Codex CLI | `0.144.3`; maintained `0.144.x` profile | `tmp/houmao-dev-testing/20260714-codex-pending-v2/codex-attempt-001/capture/recording` | 1,050 | `924ba08f576470e7a4648f895276337d83cd6fde414682bcbd75309cfff30425` | 0.05 s | none |
| Kimi Code | `0.23.6`; maintained `0.23.x` profile | `tmp/houmao-dev-testing/20260714-kimi-pending-v3/kimi-attempt-001/capture/recording` | 1,038 | `80728d5a3a6374c99578768bd4605a3c8eb18178c74077aa75de909658e594a6` | 0.05 s | none |

Claude's lifecycle metadata says `2.1.207`, but the recorded pane visibly identifies Claude Code `v2.1.209`. The pane is the direct observation of the process under test, so this qualification uses `2.1.209`. Both versions select the same maintained `2.1.x` detector profile.

## Independent Labels and Human Audit

The tracked audit labels are stored separately from the capture runner's pattern-generated labels:

- `context/features/2026-07-11-tui-state-tracking-test-plan/dataset-reports/uc-05-audited-pending-labels/claude.json`
- `context/features/2026-07-11-tui-state-tracking-test-plan/dataset-reports/uc-05-audited-pending-labels/codex.json`
- `context/features/2026-07-11-tui-state-tracking-test-plan/dataset-reports/uc-05-audited-pending-labels/kimi.json`

The maintained `terminal_record add-label` command also produced working copies under `tmp/houmao-dev-testing/20260714-pending-qualification/audited-labels/`. Each label carries an evidence note. Human review reused these videos:

- Claude: `tmp/houmao-dev-testing/20260714-claude-pending-v2/claude-attempt-001/review/labels.mp4`
- Codex: `tmp/houmao-dev-testing/20260714-codex-pending-v2/codex-attempt-001/review/labels.mp4`
- Kimi: `tmp/houmao-dev-testing/20260714-kimi-pending-v3/kimi-attempt-001/review/labels.mp4`

Contact sheets used for the boundary audit are under `tmp/houmao-dev-testing/20260714-pending-qualification/audit/`.

| Provider | Startup becomes classified | Pending onset | Last pending item consumed | Evidence at onset |
|---|---:|---:|---:|---|
| Claude | `s000014: no` | `s000048: yes` | `s001016: no` | Styled, indented queued user preview bounded above the bottom composer |
| Codex | `s000017: no` | `s000018: yes` | `s000170: no` | Bounded queued-follow-up block with its arrow item |
| Kimi | `s000018: no` | `s000086: yes` | `s001016: no` | Submitted queued row with edit/steer affordance in the prompt region |

Review covered busy/no-pending, onset, the full pending span, consumption, and the final ready return. No exact Claude suggestion string was used as an oracle.

## Canonical Replay

Analyzer output is stored beside each canonical recording as `parser_observed_qualified-source.ndjson` and `state_observed_qualified-source.ndjson`.

| Provider | Checked samples | Mismatches | Expected/actual transitions | Median interval | Maximum transition bound | Cadence-only oscillations |
|---|---:|---:|---:|---:|---:|---:|
| Claude | 1,546 | 0 | 3 / 3 | 0.109569 s | 0.128015 s | 0 |
| Codex | 1,050 | 0 | 3 / 3 | 0.105249 s | 0.124172 s | 0 |
| Kimi | 1,038 | 0 | 3 / 3 | 0.104579 s | 0.132615 s | 0 |

Every mismatch-range list is empty. All observed transition samples equal the audited source transition samples, so canonical drift is zero.

## Cadence and Capture-Delay Variants

Derived immutable streams are under `tmp/houmao-dev-testing/20260714-pending-qualification/streams/<provider>/`. Analyzer outputs use `state_observed_qual-<variant>.ndjson` and `parser_observed_qual-<variant>.ndjson` beside the corresponding canonical recording. Jitter uses seed 17, drop uses seed 31, and burst uses seed 23.

| Provider | Variant | Retained samples | Median interval | Mismatches | Observed pending transitions | Skipped audited checkpoints | Oscillations |
|---|---|---:|---:|---:|---:|---:|---:|
| Claude | 10 Hz regular | 1,545 | 0.109596 s | 0 | 3 | 0 | 0 |
| Claude | 5 Hz regular | 845 | 0.214811 s | 0 | 3 | 0 | 0 |
| Claude | 2 Hz regular | 339 | 0.516796 s | 0 | 3 | 0 | 0 |
| Claude | jitter | 851 | 0.213998 s | 0 | 3 | 0 | 0 |
| Claude | drop | 539 | 0.228305 s | 0 | 3 | 0 | 0 |
| Claude | burst | 625 | 0.114984 s | 0 | 3 | 0 | 0 |
| Codex | 10 Hz regular | 1,047 | 0.105364 s | 0 | 3 | 0 | 0 |
| Codex | 5 Hz regular | 556 | 0.208208 s | 0 | 2 | 1 | 0 |
| Codex | 2 Hz regular | 223 | 0.516575 s | 0 | 2 | 1 | 0 |
| Codex | jitter | 560 | 0.209044 s | 0 | 3 | 0 | 0 |
| Codex | drop | 363 | 0.222541 s | 0 | 2 | 1 | 0 |
| Codex | burst | 428 | 0.110930 s | 0 | 3 | 0 | 0 |
| Kimi | 10 Hz regular | 1,036 | 0.104671 s | 0 | 3 | 0 | 0 |
| Kimi | 5 Hz regular | 549 | 0.207264 s | 0 | 3 | 0 | 0 |
| Kimi | 2 Hz regular | 220 | 0.514615 s | 0 | 3 | 0 | 0 |
| Kimi | jitter | 553 | 0.207334 s | 0 | 3 | 0 | 0 |
| Kimi | drop | 360 | 0.219948 s | 0 | 3 | 0 | 0 |
| Kimi | burst | 413 | 0.111103 s | 0 | 3 | 0 | 0 |

All reported transitions remained within the computed cadence bound. Codex's audited `s000017: no` surface exists for one source frame immediately before `s000018: yes`; 5 Hz, 2 Hz, and seeded drop omit that frame. The validator reports it under `skipped_unobserved_labels` and still evaluates every retained sample.

## One/Two/Three-Pending Engineering Matrix

These runs test provider queue rendering and public presence semantics. Their existing labels were generated from capture patterns, so mismatch counts below diagnose that engineering oracle; they are not substituted for the independent canonical labels.

| Provider | Target/observed | Recording root | SHA-256 | Samples | Tracker `yes` samples | Pattern mismatches | Status |
|---|---|---|---|---:|---:|---:|---|
| Claude | 1 / 1 | `tmp/houmao-dev-testing/20260714-claude-1-pending/claude-attempt-001` | `2851ec9174238fde0170e9d77899069d698bcab94224cceeddd886fe4326d42d` | 1,595 | 1,004 | 0 | pass |
| Claude | 2 / 1 | `tmp/houmao-dev-testing/20260714-claude-2-pending/claude-attempt-001` | `dd4e7cd82d6ed19e3d0b879c8b7cacb288ec6d6e2b3e9e7ec0499bc260501d60` | 184 | 42 | 4 | tainted: queue capped at 1 |
| Claude | 3 / 1 | `tmp/houmao-dev-testing/20260714-claude-3-pending-long/claude-attempt-001` | `fc5df438b4e3d3c6ea27f69209a80f9e79aaea9f6fd3aed0d1891c444dd07ad7` | 462 | 125 | 12 | tainted: queue capped at 1 |
| Codex | 1 / 1 | `tmp/houmao-dev-testing/20260714-codex-1-pending/codex-attempt-001` | `61449dc12d0d106758b81b2b6e14db7f5e4d2a7e7b0828beb704e23f56d0bbd8` | 684 | 41 | 530 | pass; old pattern has a stale-arrow false positive |
| Codex | 2 / 2 | `tmp/houmao-dev-testing/20260714-codex-2-pending/codex-attempt-001` | `26b53c97aad9dcd8349658b781ea0b0bfdc71aa94e67ed20ed7c29ee38f12ee4` | 1,091 | 126 | 0 | pass |
| Codex | 3 / 3 | `tmp/houmao-dev-testing/20260714-codex-3-pending-long/codex-attempt-001` | `78edbc5f50d8b919448bf9e46ad3205129a16bba5183eca157cea8e39c54cc9c` | 1,178 | 134 | 0 | pass |
| Kimi | 1 / 1 | `tmp/houmao-dev-testing/20260714-kimi-1-pending/kimi-attempt-001` | `a94a8a55a4d5f133dbbbb945639d8b7287ac83c72d09de9709956e25588756db` | 1,495 | 919 | 0 | pass |
| Kimi | 2 / 2 | `tmp/houmao-dev-testing/20260714-kimi-2-pending-v2/kimi-attempt-001` | `bb340d1dc7d27fdf74b6115d4d7f265f29cbbd0566db8af56d2c81c61cd9f381` | 1,951 | 1,368 | 0 | pass |
| Kimi | 3 / 3 | `tmp/houmao-dev-testing/20260714-kimi-3-pending-long-v4/kimi-attempt-001` | `fc9962b0a0dc4774a88462d1342a7ddaa3ff52e3cc7ba14467e0b0cb1de3ecf2` | 2,922 | 1,964 | 0 | tainted: non-fatal `active` pattern timeout |

The Claude pattern mismatches occur while an already queued item remains visible but the runner temporarily labels `no` during injection of another prompt. The Codex one-item pattern matches a later `↳ Interacted with background terminal` transcript row after the real queued-follow-up block has been consumed. The profile-owned detectors correctly require provider-specific bounded queue structure and avoid both errors.

Every matrix run has a review video at `<recording-root>/review/labels.mp4`. Current replay output is at `<recording-root>/capture/recording/state_observed_qualified-count.ndjson`.

## Conclusion

UC-05 replay qualification passes for the three maintained providers. The detector remains conservative on incomplete surfaces, recognizes provider-owned pending structure, clears after consumption, survives the required cadence variations, and does not confuse queue depth or stale transcript content with current pending-input presence. No Gemini surface was tested.
