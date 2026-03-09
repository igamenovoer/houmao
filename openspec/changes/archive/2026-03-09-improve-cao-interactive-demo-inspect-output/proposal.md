## Why

The interactive CAO demo now starts reliably with a per-run trusted home, but the `inspect` surface still exposes that runtime state poorly. Its human-readable output is hard to scan, and it currently advertises a `tail -f ~/.aws/...` command that can be wrong because this demo intentionally runs CAO with `HOME` set to the per-run workspace root rather than the operator's real home directory.

## What Changes

- Make the interactive demo `inspect` output present the live session as an operator-oriented surface instead of a sparse state dump.
- Derive the terminal log path for the interactive demo from the demo's configured CAO home/run root so the suggested `tail -f` command matches the actual file created by the launched CAO server.
- Include the live Claude Code state in `inspect`, sourced from the CAO terminal status when available, so operators can immediately see whether the session is idle, processing, waiting for input, or errored.
- Add `inspect --with-output-text <num-tail-chars>` so operators can request the current tail of the clean projected Claude TUI output text without reading raw ANSI/tmux scrollback.
- Update the interactive demo README and verification/snapshot contract so the documented and validated log-path behavior matches the per-run trusted-home layout introduced by the startup hardening work.
- Preserve machine-readable inspection data while making the default console output easier to read during manual tmux/log inspection.

## Capabilities

### New Capabilities
- `cao-interactive-demo-inspect-surface`: Operator-facing inspection output and log-path contract for the interactive CAO full-pipeline demo.

### Modified Capabilities
- None.

## Impact

- Affected code: `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py`, `src/gig_agents/agents/brain_launch_runtime/backends/claude_code_shadow.py` (or shared parser helpers it reuses), `scripts/demo/cao-interactive-full-pipeline-demo/README.md`, `scripts/demo/cao-interactive-full-pipeline-demo/expected_report/report.json`, and `scripts/demo/cao-interactive-full-pipeline-demo/scripts/verify_report.py`.
- Affected integrations: `run_demo.sh inspect` will need a live CAO terminal-status lookup using the persisted `cao_base_url` and `terminal_id`.
- Affected operator behavior: `inspect` gains an opt-in live-output tail surface for clean Claude dialog text.
- Affected tests: `tests/unit/demo/test_cao_interactive_full_pipeline_demo.py` and any integration/manual checks that assert the `inspect` surface or report shape.
- Affected systems: the operator-facing `run_demo.sh inspect` workflow, CAO trusted-home path semantics, and the maintainer verification snapshot for this demo pack.
