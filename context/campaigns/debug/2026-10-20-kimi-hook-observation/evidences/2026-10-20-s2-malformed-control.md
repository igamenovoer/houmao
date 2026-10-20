# Evidence: S2 malformed-config control — silent section drop (kimi 2.2.0)

Date: 2026-10-20. Iteration: [iteration 1](../iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md). Arm: S2. Key questions: [KQ-1](../key-questions/KQ-1-config-injection-coexistence.md), [KQ-3](../key-questions/KQ-3-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/kimi-hook-capture/s2/run-20261020T133534Z/` (tmux `kimihook-s2-3896518`, pane `%224`) |
| Tool | kimi 2.2.0, `--auto`; scratch home with 20 valid observer entries plus one malformed entry with an extra `cwd = "/tmp"` key |
| Collector | gen 1, port 38821, **0 accepted events** |
| Recording | 60 samples; labels `s2-startup`, `s2-print-probe` |
| Headless probe | `kimi -p "Reply with exactly: OK"`, rc 0 in 4.079 s |

## TUI Run

| Fact | Value |
| --- | --- |
| Ready composer | 2.872 s, zero keypresses |
| Prompt | `Reply with exactly: OK` |
| Pane answer | `● OK` visible from sample `s000045` (11.02 s); provider unaffected |
| TUI hook warning | **none** — no warning surface, no config error, no toast |
| Hook events | **0** before and after the turn |
| Exit | `/exit` in 0.965 s; no `SessionEnd` (channel dead) |

The whole `[[hooks]]` section was silently dropped by the strict schema. The TUI gives the operator no indication that the observation channel is dead.

## Headless Probe (paired, same malformed home)

Stderr:

```text
kimi version 2.2.0
Warning: Ignored invalid config section 'hooks': [
  {
    "code": "unrecognized_keys",
    "keys": ["cwd"],
    "path": [20],
    "message": "Unrecognized key: \"cwd\""
  }
]
• The user wants exactly "OK".

To resume this session: kimi -r session_23e9a4b7-5621-47ea-9515-3bd6a9ff86b7
```

| Fact | Value |
| --- | --- |
| Warning visibility | print-mode **stderr only**; `warning_mentions_hooks=true` |
| Entry index | `path: [20]` — the 21st entry (0-based index 20), i.e. the appended malformed one |
| Exit code | 0; stdout `• OK` |
| Hook events | 0 |

## Verdict

**PASS as control.** One malformed entry voids the entire hooks section with a warning diagnostic only; the session itself is normal. The observation channel dies silently in the TUI and is visible only in print-mode stderr. This is the failure mode the production installer must detect by strict read-back.

## Harness Corrections (2026-10-20)

- No S2-specific correction. The runner appends the malformed entry through `append_raw_toml_block()` without validation, as designed.

## Cleanup

`kimihook-s2-3896518` exited via `/exit`; runner teardown stopped the collector. Run root retained under `tmp/kimi-hook-capture/s2/`.
