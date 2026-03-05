# Demo Validation: CAO Claude Session

Date: 2026-02-28
Change: `agent-brain-launch-runtime-claude-cli-contracts`

## Command

```bash
scripts/demo/cao-claude-session/run_demo.sh
```

## Claude Code Version

```bash
claude --version
# 2.1.62 (Claude Code)
```

## Results

### Attempt 1

- Status: `SKIP`
- Workspace: `tmp/demo_cao_claude_20260228_064515_688745`
- Reason emitted by demo runner: `connectivity unavailable`
- Failure symptom:
  - CAO `GET /terminals/<id>/output?mode=last` returned `404`
  - Detail: `No Claude Code response found - no ⏺ pattern detected`

### Attempt 2 (after CAO output fallback fix)

- Status: `PASS`
- Workspace: `tmp/demo_cao_claude_20260228_065232_705668`
- Demo output included:
  - `verification passed`
  - `demo complete`
  - report written to `.../report.json`

## Notes

- Added CAO runtime fallback behavior: when `mode=last` output is unavailable (`404`), retry `mode=tail` then `mode=full` before failing.
- After this fallback change, the required end-to-end demo completed successfully.
