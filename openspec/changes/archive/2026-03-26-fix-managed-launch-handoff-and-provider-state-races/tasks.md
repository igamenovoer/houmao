## 1. Resume Intent And Provider-State Safety

- [x] 1.1 Introduce an explicit launch-plan or resume intent boundary so read-only resumed local control does not reapply unattended provider-home mutations for already-live sessions.
- [x] 1.2 Thread that intent through local managed-agent control entrypoints such as state, show, prompt, interrupt, gateway status, and gateway attach while preserving provider-start and relaunch bootstrap behavior.
- [x] 1.3 Replace strategy-owned JSON and TOML provider-state writes with serialized per-home atomic replacement helpers, including explicit repair handling for declared owned files during provider-start or relaunch.

## 2. libtmux Launch Handoff

- [x] 2.1 Add a repo-owned libtmux-first tmux handoff helper for managed launch that resolves the target session through libtmux and uses libtmux-owned command dispatch when interactive attach is needed.
- [x] 2.2 Add explicit caller interactivity detection to `houmao-mgr agents launch` so non-interactive callers skip tmux attach while still reporting successful launch coordinates.
- [x] 2.3 Update launch-time success reporting so interactive and non-interactive callers both preserve the existing provider-readiness checks while exposing enough tmux identity for later manual attach.

## 3. Regression Coverage

- [x] 3.1 Add unit or integration coverage proving non-headless `houmao-mgr agents launch` does not surface `open terminal failed: not a terminal` when the caller has no usable TTY.
- [x] 3.2 Add concurrency regression coverage for simultaneous resumed local control commands against the same unattended Claude runtime home so no malformed strategy-owned JSON read is observed.
- [x] 3.3 Add relaunch or provider-start repair coverage for blank strategy-owned Claude files and verify the finished files are made visible through atomic replacement.

## 4. Validation And Operator Docs

- [x] 4.1 Update relevant CLI and tmux operator docs to describe non-interactive managed launch behavior and the libtmux-backed handoff contract.
- [x] 4.2 Re-run the live repros: non-interactive serverless Claude launch, concurrent `agents state` plus `agents gateway status`, and foreground gateway attach after launch.
