## 1. Registry Cleanup Defaulting

- [x] 1.1 Change the native `houmao-mgr admin cleanup registry` and `admin cleanup-registry` flag contract so tmux checking is enabled by default and `--no-tmux-check` becomes the explicit opt-out.
- [x] 1.2 Update registry-cleanup payload building and help text so the effective tmux-check mode is reported consistently after the flag flip.

## 2. Stale Classification And Tests

- [x] 2.1 Update shared-registry cleanup classification so lease-fresh tmux-backed records whose owning tmux session is absent locally are removable by default.
- [x] 2.2 Add or revise unit coverage for default tmux-probe removal, probe-confirmed preservation, and `--no-tmux-check` lease-only preservation.

## 3. Documentation And Verification

- [x] 3.1 Update CLI and registry cleanup docs to describe tmux probing as the default behavior and `--no-tmux-check` as the opt-out path.
- [x] 3.2 Run targeted registry cleanup and native CLI help-surface tests and confirm `openspec status --change default-registry-cleanup-tmux-probe` is apply-ready.
