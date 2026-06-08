## Kimi Code TUI Probe Notes

Date: 2026-06-08

Local source and installed-tool checks used for this change:

- Local source reference: `extern/orphan/kimi-code`.
- Installed Kimi Code command: `/home/huangzhe/.kimi-code/bin/kimi`.
- Observed installed version in the change design: `0.11.0`.
- Kimi command docs in the local source confirm `--continue`, `--session <session_id>`, `--model <alias>`, `--yolo`, `--auto`, `--plan`, `--skills-dir`, and `KIMI_CODE_NO_AUTO_UPDATE`.
- The local source documents that bare `--session` opens the interactive session picker; managed relaunch therefore only uses `--session <session_id>`.
- The local source documents that `--continue` or `--session` cannot be combined with `--yolo`, `--auto`, or `--plan`; Houmao rejects these combinations before provider start.
- Existing Kimi prompt-mode `--skills-dir` behavior remains scoped to `kimi_headless`; Kimi TUI launch does not receive managed `--skills-dir` args.
