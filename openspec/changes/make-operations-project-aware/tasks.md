## 1. Centralize project-aware root selection and bootstrap

- [x] 1.1 Extend `src/houmao/project/overlay.py` so the active overlay adds first-class `runtime_root` and `jobs_root`, reuses the existing `mailbox_root` and `easy_root` properties, and provides one shared ensure-or-bootstrap path that applies `CLI > HOUMAO_PROJECT_OVERLAY_DIR > nearest ancestor overlay inside the current Git worktree boundary inferred from the nearest ancestor .git file or directory > bootstrap <cwd>/.houmao`.
- [x] 1.2 Introduce one shared project-aware local-roots bundle that computes overlay-local defaults for `agents/`, `runtime/`, `jobs/`, and `mailbox/`, then threads those defaults into `src/houmao/owned_paths.py` at the default tier so explicit CLI and env overrides still win while registry resolution stays shared unless explicitly or environmentally redirected.
- [x] 1.3 Update project root-reporting and selection payloads in `src/houmao/srv_ctrl/commands/project.py` so stateful project-aware commands can ensure/bootstrap the active overlay, `project status` remains non-creating, and implicit bootstrap surfaces the created overlay root in text/JSON output.

## 2. Move build and launch flows onto overlay-local runtime and jobs roots

- [x] 2.1 Update `src/houmao/srv_ctrl/commands/brains.py`, `src/houmao/agents/brain_builder.py`, and related build helpers so project-context brain homes and manifests default under `<overlay>/runtime` when no stronger override is present.
- [x] 2.2 Update `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/agents/realm_controller/runtime.py`, and `src/houmao/srv_ctrl/commands/runtime_artifacts.py` so local launches and session startup pass explicit overlay-local runtime defaults plus an explicit jobs-root or resolved job-dir input instead of falling back to shared runtime or working-directory jobs defaults.
- [x] 2.3 Update `src/houmao/srv_ctrl/commands/project.py` easy-instance launch paths and other project-managed local launch surfaces to reuse the shared project-aware resolver instead of `_require_project_overlay()` failure paths.

## 3. Make mailbox, cleanup, and server operations follow the same contract

- [x] 3.1 Update `src/houmao/srv_ctrl/commands/mailbox.py`, `src/houmao/agents/mailbox_runtime_support.py`, and runtime mailbox bootstrap paths so generic mailbox operations default to `<overlay>/mailbox` in project context while preserving explicit mailbox-root and mailbox env-var overrides.
- [x] 3.2 Update `src/houmao/srv_ctrl/commands/runtime_cleanup.py`, `src/houmao/srv_ctrl/commands/admin.py`, and related cleanup helpers so project-context runtime maintenance defaults to the overlay-local runtime root, remains single-root-per-invocation, and still lets operators target legacy shared-root artifacts via explicit `--runtime-root` overrides while registry cleanup remains shared-root aware.
- [x] 3.3 Update `src/houmao/cao/server_launcher.py`, `src/houmao/server/commands/common.py`, `src/houmao/server/config.py`, `src/houmao/passive_server/config.py`, and maintained server lifecycle commands so project-context runtime artifacts resolve under `<overlay>/runtime` unless explicitly overridden.

## 4. Remove remaining split-root assumptions from maintained workflows

- [ ] 4.1 Audit maintained `houmao-mgr project ...` and project-managed easy-instance flows for direct shared-root resolution or hard `project init` prerequisites and route them through the shared project-aware resolver.
- [x] 4.2 Audit maintained `houmao-mgr brains ...`, `houmao-mgr agents launch ...`, and local runtime-artifact launch surfaces for shared-root or working-directory job-root assumptions that must now resolve through the shared project-aware contract.
- [x] 4.3 Audit maintained `houmao-mgr mailbox ...` and `houmao-mgr admin cleanup ...` families for remaining split-root assumptions and make the project-context versus explicit-override behavior consistent.
- [x] 4.4 Audit maintained `houmao-mgr server ...` and `houmao-server` startup/config surfaces for shared runtime-root assumptions, while leaving deprecated compatibility entrypoints out of scope for this change.
- [ ] 4.5 Update maintained demos and helper scripts that currently need multiple root env vars only to keep one workflow self-contained so they rely on overlay-local defaults where the new contract makes that possible.
- [ ] 4.6 Refresh user-facing help text, error messages, and JSON payloads so they describe the new project-aware contract consistently across project, launch, mailbox, cleanup, and server surfaces, including notices for implicit overlay bootstrap.

## 5. Update docs and verify the new contract end to end

- [x] 5.1 Update active reference and getting-started docs that currently describe shared runtime, shared mailbox, working-directory jobs, or mandatory `project init` bootstrapping so they document the new overlay-local contract and the registry-only shared default.
- [ ] 5.2 Add or update unit and integration coverage for overlay-selection precedence, nearest-ancestor reuse, `.git`-marker worktree boundary handling for nested repos, `project status` remaining non-creating, implicit bootstrap notices, overlay-local build/runtime/jobs placement, mailbox defaults, single-root cleanup defaults plus explicit shared-root cleanup overrides, and server-start behavior in project context.
- [ ] 5.3 Run focused validation for the changed command families, verify representative demo or interactive workflows still work with fewer root env overrides, and re-run `openspec status --change make-operations-project-aware` to confirm the change is apply-ready.
