## 1. Fix the runtime and launcher blockers behind the demo

- [x] 1.1 Update mailbox-enabled runtime startup so bootstrap or registration confirmation happens before launch-plan mailbox env binding depends on the active registration, keep registration-dependent path resolution strict instead of adding fallback path synthesis, document the bootstrap-first invariant in code, and add regression coverage for starting two mailbox-enabled sessions sequentially on the same initialized shared mailbox root.
- [x] 1.2 Update launcher config parsing and effective-home derivation so an omitted or empty `home_dir` means the launcher-derived system-defined home, and add unit coverage for that normalization behavior.
- [x] 1.3 Change `config/cao-server-launcher/local.toml` to use explicit `home_dir = ""` as the portable default instead of the current machine-specific `/data/agents/cao-home` path, and add coverage that the checked-in config works in an environment without `/data/agents/`.

## 2. Refresh the mailbox tutorial pack around launcher-managed CAO

- [x] 2.1 Update `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh` and `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/tutorial_pack_helpers.py` so the default loopback path writes a demo-local launcher config, manages CAO through helper-owned Python commands, validates ownership on reuse, resolves `--cao-profile-store` from the demo-local launcher context, and stops launcher-managed CAO on cleanup when this run started it, including interrupted or partial-start exits.
- [x] 2.2 Keep the tutorial's external-CAO escape hatch explicit: when the caller points the pack at a non-loopback or intentionally external CAO service, the runner should skip local launcher ownership and fail or skip with clear `SKIP:`/`FAIL:` profile-store guidance instead of silently guessing.
- [x] 2.3 Extend the tutorial's report generation and sanitization so it captures and masks the demo-local CAO launcher artifacts and the latest mailbox-local state artifact locations consistently.

## 3. Update the tutorial story to match the latest mailbox model

- [x] 3.1 Update the tutorial README to explain the shared `index.sqlite` versus per-mailbox `mailbox.sqlite` split, the new mailbox-local env-binding expectations, and the fact that the roundtrip remains gateway-optional.
- [x] 3.2 Update the README prerequisites and walkthrough so the default path describes launcher-managed local CAO rather than assuming an ambient CAO service that the operator preconfigured manually.
- [x] 3.3 Add helper-based verification checks that both tutorial mailboxes materialize mailbox-local `mailbox.sqlite` state via mailbox-module path resolution, and verify that the tutorial still succeeds through runtime `mail` commands without requiring gateway attach or notifier enablement.

## 4. Validate the new end-to-end story

- [x] 4.1 Add or update tutorial-pack unit and integration tests for helper-owned launcher-managed CAO startup, ownership-mismatch recovery, cleanup after interrupted or partial-start runs, demo-local profile-store alignment, mailbox-local artifact verification, and report sanitization.
- [x] 4.2 Run targeted runtime, launcher, and tutorial-pack test slices that cover the startup-order fix, the portable launcher-home contract, and the refreshed tutorial workflow.
- [x] 4.3 Run `pixi run openspec validate --strict --json --type change stabilize-mailbox-roundtrip-tutorial-pack-after-local-state`.
