Houmao 3.0.0rc3 introduces four managed run modes and unified control through the manager and authenticated gateway.

## Upgrade From 3.0.0rc2

- Stop existing agents with RC2 before upgrading. Launch fresh sessions in RC3, which uses launch plan schema 3, session manifest schema 6, agent registry schema 5, and execution locator schema 2.
- Replace `defaults.posture.headless` in launch profiles with `defaults.posture.mode`, or select a mode on launch with `--mode`. An existing DSH ACP workflow maps to `service`. Choose `headless` for one-shot DSH CLI calls. [Session Lifecycle Guide](https://igamenovoer.github.io/houmao/reference/run-phase/session-lifecycle/)

## What Changed

- `headless` runs one CLI worker per prompt, `service` keeps a native protocol process alive across prompts, `tui` provides a terminal UI, and `web` provides a browser UI. The launch result reports the selected mode and the available browser or terminal handoff. [Run Modes and Backends](https://igamenovoer.github.io/houmao/reference/run-phase/backends/)
- DeepSeek Harness adds native one-shot headless execution and persistent ACP. Kimi Code 2.6.0 adds ACP service and Web modes. Codex CLI 0.169.0 adds app-server service.
- The manager and signed gateway share prompt admission and lifecycle control through the current execution owner. Passive API and AG-UI clients can observe supported sessions and their outcomes.
- Kimi Web uses one native conversation for the browser and Houmao. The owner checks readiness before sending. If the browser sends first after that check, Houmao reports the queued receipt from Kimi. [Kimi Web Guide](https://igamenovoer.github.io/houmao/reference/run-phase/kimi-web/)

## Install the Candidate

```bash
uv tool install 'houmao==3.0.0rc3'
npx skills add https://github.com/igamenovoer/houmao-skills#v3.0.0rc3
```

## Qualification

The candidate passed 4,944 unit tests with 14 skips. The affected integration batch passed 50 cases. Lint, type checking, strict docs build, and distribution validation passed. The broader legacy CLI shape suite had 17 failures that also reproduced on its base revision. [CLI verification log](https://github.com/igamenovoer/houmao/blob/v3.0.0rc3/openspec/changes/archive/2026-11-19-run-modes-01-introduce-managed-agent-run-modes/logs/implementation.md)

The native DSH, Kimi, and Codex paths were exercised with self-hosted Qwen3.8. Kimi Web qualification covered browser and gateway prompts, busy rejection, interruption, and exact relaunch. [Kimi Web verification log](https://github.com/igamenovoer/houmao/blob/v3.0.0rc3/openspec/changes/archive/2026-11-19-run-modes-07-add-kimi-web-mode/logs/check-and-send.md)

[Compare v3.0.0rc2 and v3.0.0rc3](https://github.com/igamenovoer/houmao/compare/v3.0.0rc2...v3.0.0rc3)
