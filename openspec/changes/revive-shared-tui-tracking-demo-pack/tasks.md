## 1. Restore The Supported Demo Surface

- [ ] 1.1 Create the restored supported demo directories under `scripts/demo/shared-tui-tracking-demo-pack/` and `src/houmao/demo/shared_tui_tracking_demo_pack/`, carrying forward the pack’s runner, config, scenario, reporting, and contract docs from the archived implementation.
- [ ] 1.2 Add a tracked secret-free `inputs/agents/` tree for the restored pack with canonical `skills/`, `roles/`, and `tools/` layout for the shared interactive-watch role across Claude and Codex.
- [ ] 1.3 Update `scripts/demo/README.md` and the restored pack README/docs so the supported operator surface points only at the non-legacy demo location while leaving `legacy/` clearly archival.

## 2. Rewire Launch Bootstrap To Demo-Local Agent Assets

- [ ] 2.1 Add a demo-specific helper that materializes `workdir/.agentsys/agents` from the tracked `inputs/agents/` tree for each live-watch or recorded-capture run.
- [ ] 2.2 Materialize one selected-tool demo-local auth alias named `default` inside the generated agent tree from host-local fixture auth bundles, with clear preflight errors when the expected source bundle is missing.
- [ ] 2.3 Update live-watch and recorded-capture build paths to use the generated run-local agent-definition directory instead of `tests/fixtures/agents/`.

## 3. Restore Live Watch And Recorded Validation Workflows

- [ ] 3.1 Repoint the driver, `run_demo.sh`, and dashboard self-launch wiring to the restored supported module and script paths.
- [ ] 3.2 Preserve and verify demo-config resolution, recorder-optional live watch, scenario-driven capture, replay comparison, sweep behavior, and ownership-based cleanup under the restored pack.
- [ ] 3.3 Add explicit preflight behavior for missing or empty committed fixture roots so `recorded-validate-corpus` and related commands fail clearly instead of relying on absent historical corpus contents.

## 4. Verify And Harden The Restored Pack

- [ ] 4.1 Add targeted automated coverage for generated agent-tree materialization, auth alias projection, and launch preflight behavior.
- [ ] 4.2 Add targeted workflow coverage for live-watch startup and recorded-capture / recorded-validate flows using the restored demo-local agent-definition source.
- [ ] 4.3 Run targeted tests and operator smoke checks, then confirm the restored docs and artifacts no longer rely on the legacy path or on direct `tests/fixtures/agents/` bootstrap.
