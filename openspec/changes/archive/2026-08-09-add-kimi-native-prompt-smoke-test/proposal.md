## Why

The `use-kimi-native-system-prompt` change landed the native `$KIMI_CODE_HOME/SYSTEM.md` role-prompt contract with full hermetic unit coverage, but nothing yet proves end-to-end that a Houmao-managed agent launch actually delivers the composed role prompt into a real Kimi Code 0.34.x agent. A fast, disposable smoke check is needed before committing to the heavier recorded-corpus qualification (tasks 5.3–5.4 of that change).

## What Changes

- Add development-only smoke-test scripts under `tmp/kimi-native-prompt-smoke/` that build a minimal Houmao managed agent (Kimi brain) with a frozen marker role, launch the real Kimi Code 0.34.x binary (headless and TUI), and verify the injected system prompt reaches the agent.
- Use Kimi **auto credentials**: reuse the credential state the installed `kimi` CLI natively discovers (the machine's Kimi Code home), imported into Houmao through the system-skill contract (`houmao-shared-routines->houmao-credential-mgr`, Kimi kind 4 "Existing Kimi Code Home" → `--code-home`); validate posture non-secretly (`kimi provider list --json`, `kimi doctor config`), never print credential JSON, and never run login flows.
- Verify provider-native evidence, not chat claims: assert `SYSTEM.md` bytes, `${base_prompt}` preservation, effective/rendered digests, `KIMI_CODE_LEGACY_FLAG=0`, and provider-start verification provenance before any prompt submission; then confirm the agent's first response is consistent with the frozen role marker.
- Cover both launch surfaces in scope: one headless turn and one unattended TUI session, plus a supported relaunch digest check.
- Use a subagent to label the recorded TUI session's tracked states (blind labeling before any replay), keeping the maintainer-labeling contract without blocking on human time.
- No schema, CLI, or documentation changes; scripts and evidence live under the gitignored `tmp/` tree.
- **Scope revision during implementation**: one product robustness fix landed after live testing exposed it — the tmux pane wrapper in the headless turn and TUI launch paths changed from `sh -lc` to `bash -lc` (`headless_runner.py`, `local_interactive.py`). On dash-as-`/bin/sh` systems the login profile chain aborted the pane command before it ran, killing every tmux-backed turn. Pre-existing unit tests failed on such machines for the same reason and now pass.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This change adds development-only smoke scripts under `tmp/`; no spec-level behavior changes, so the change opts out of spec deltas via `skip_specs: true`.

## Impact

- New files only under `tmp/kimi-native-prompt-smoke/` (gitignored; not packaged, not shipped).
- Consumes existing surfaces: `src/houmao/agents/kimi_system_prompt.py` behavior, managed brain build/launch flows, `houmao-mgr project credentials kimi add --code-home` auto-credential import, `tools.terminal_record` for TUI capture.
- Feeds evidence into `use-kimi-native-system-prompt` task 5.5 (live integration) and de-risks tasks 5.3–5.4; it does not replace the full recorded-corpus qualification.
- Requires a local Kimi Code 0.34.0+ binary (confirmed: `kimi` 0.34.0 on this machine) with coherent native auto credential state in its Kimi Code home; live runs consume provider API quota.
