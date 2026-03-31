## 1. Centralize project-aware root selection and bootstrap

- [ ] 1.1 Extend `src/houmao/project/overlay.py` so the active overlay exposes first-class `runtime`, `jobs`, `mailbox`, and `easy` roots and add one shared ensure-or-bootstrap path that applies `CLI > HOUMAO_PROJECT_OVERLAY_DIR > nearest ancestor overlay inside the current Git worktree > bootstrap <cwd>/.houmao`.
- [ ] 1.2 Introduce one shared project-aware local-root resolver that returns overlay-local defaults for `agents/`, `runtime/`, `jobs/`, and `mailbox/` while keeping registry resolution shared in `src/houmao/owned_paths.py` unless an explicit or env override redirects it.
- [ ] 1.3 Update project root-reporting and selection payloads in `src/houmao/srv_ctrl/commands/project.py` so commands report the new overlay-local roots and no longer treat prior manual `project init` as a prerequisite for stateful project-aware workflows.

## 2. Move build and launch flows onto overlay-local runtime and jobs roots

- [ ] 2.1 Update `src/houmao/srv_ctrl/commands/brains.py`, `src/houmao/agents/brain_builder.py`, and related build helpers so project-context brain homes and manifests default under `<overlay>/runtime` when no stronger override is present.
- [ ] 2.2 Update `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/agents/realm_controller/runtime.py`, and `src/houmao/srv_ctrl/commands/runtime_artifacts.py` so local launches and session startup pass explicit overlay-local runtime and jobs roots instead of falling back to shared runtime or working-directory jobs defaults.
- [ ] 2.3 Update `src/houmao/srv_ctrl/commands/project.py` easy-instance launch paths and other project-managed local launch surfaces to reuse the shared project-aware resolver instead of `_require_project_overlay()` failure paths.

## 3. Make mailbox, cleanup, and server operations follow the same contract

- [ ] 3.1 Update `src/houmao/srv_ctrl/commands/mailbox.py`, `src/houmao/agents/mailbox_runtime_support.py`, and runtime mailbox bootstrap paths so generic mailbox operations default to `<overlay>/mailbox` in project context while preserving explicit mailbox-root and mailbox env-var overrides.
- [ ] 3.2 Update `src/houmao/srv_ctrl/commands/runtime_cleanup.py`, `src/houmao/srv_ctrl/commands/admin.py`, and related cleanup helpers so project-context runtime maintenance defaults to overlay-local runtime and jobs roots while registry cleanup remains shared-root aware.
- [ ] 3.3 Update `src/houmao/cao/server_launcher.py`, `src/houmao/server/commands/common.py`, `src/houmao/server/config.py`, `src/houmao/passive_server/config.py`, and maintained server lifecycle commands so project-context runtime artifacts resolve under `<overlay>/runtime` unless explicitly overridden.

## 4. Remove remaining split-root assumptions from maintained workflows

- [ ] 4.1 Audit maintained `houmao-mgr` local command families for direct calls to shared-root helpers or hard-coded `project init` prerequisites and route them through the shared project-aware resolver.
- [ ] 4.2 Update maintained demos and helper scripts that currently need multiple root env vars only to keep one workflow self-contained so they rely on overlay-local defaults where the new contract makes that possible.
- [ ] 4.3 Refresh user-facing help text, error messages, and JSON payloads so they describe the new project-aware contract consistently across project, launch, mailbox, cleanup, and server surfaces.

## 5. Update docs and verify the new contract end to end

- [ ] 5.1 Update active reference and getting-started docs that currently describe shared runtime, shared mailbox, working-directory jobs, or mandatory `project init` bootstrapping so they document the new overlay-local contract and the registry-only shared default.
- [ ] 5.2 Add or update unit and integration coverage for overlay-selection precedence, nearest-ancestor reuse, Git/worktree boundary handling for nested repos, auto-bootstrap, overlay-local build/runtime/jobs placement, mailbox defaults, cleanup defaults, and server-start behavior in project context.
- [ ] 5.3 Run focused validation for the changed command families, verify representative demo or interactive workflows still work with fewer root env overrides, and re-run `openspec status --change make-operations-project-aware` to confirm the change is apply-ready.
