## 1. CAO Context Alignment In Demo Scripts

- [x] 1.1 Add explicit CAO profile-store path resolution to `scripts/demo/cao-codex-session/run_demo.sh`, `scripts/demo/cao-claude-tmp-write/run_demo.sh`, and `scripts/demo/cao-claude-esc-interrupt/run_demo.sh`.
- [x] 1.2 Pass the resolved profile-store path to `start-session` (`--cao-profile-store`) in all three CAO session demos.
- [x] 1.3 Ensure CAO lifecycle control in those demos uses `python -m gig_agents.cao.tools.cao_server_launcher` (`status`/`start`/`stop`) as the only server-management path.
- [x] 1.4 Update local loopback startup handling in those demos so untracked healthy `cao-server` reuse is handled deterministically via launcher-driven logic (retry/fail-fast) without ad-hoc process signaling.

## 2. Skip Classification And Operator Diagnostics

- [x] 2.1 Update skip classifiers in affected demos so profile-load failures (`Agent profile not found` / `Failed to load agent profile`) are not labeled as missing credentials.
- [x] 2.2 Ensure startup logs/messages expose CAO context details needed for troubleshooting (at minimum profile-store/home context and ownership mismatch signals).
- [x] 2.3 Verify behavior consistency with `scripts/demo/cao-claude-session/run_demo.sh` launcher-module lifecycle semantics where applicable.

## 3. Documentation And Validation

- [x] 3.1 Update README files for `cao-codex-session`, `cao-claude-tmp-write`, and `cao-claude-esc-interrupt` to document profile-store alignment and local CAO ownership behavior.
- [x] 3.2 Run targeted demo validation sequentially (single-port CAO): `cao-codex-session`, `cao-claude-tmp-write`, `cao-claude-esc-interrupt`, and confirm skip/fail reasons match new taxonomy.
- [x] 3.3 Run shell syntax checks (`bash -n`) for touched demo scripts and record outcomes in implementation notes/PR description.
