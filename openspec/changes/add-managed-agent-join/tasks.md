## 1. Native CLI join flow

- [x] 1.1 Add `houmao-mgr agents join` to the native CLI and parse the TUI vs `--headless` join forms around `--agent-name`, optional `--agent-id`, optional or required `--provider`, repeatable `--launch-args`, repeatable Docker-style `--launch-env`, optional `--working-directory`, and optional headless `--resume-id` with `none`/`last`/exact-id semantics.
- [x] 1.2 Implement join-time tmux inspection that resolves the current tmux session, targets window `0`, pane `0`, derives the pane current path, and detects supported live TUI providers from the primary pane process tree.
- [x] 1.3 Make join fail closed with explicit operator errors and cleanup of newly created partial artifacts when tmux context or required adoption inputs are missing, inconsistent, or unsupported.

## 2. Joined-session runtime artifacts

- [x] 2.1 Add a join-derived `LaunchPlan` construction path for adopted sessions and keep any placeholder `brain_manifest.json` out of runtime behavioral truth.
- [x] 2.2 Extend session-manifest v4 boundary models with backward-compatible joined-session fields, including explicit `posture_kind`, structured TUI launch options, structured headless launch options, Docker-style env specs, and backend-specific resume-selection state for no-known-chat, `last`, or one exact provider id.
- [x] 2.3 Regenerate the packaged session-manifest schema and update schema-consistency coverage after the boundary-model changes.
- [x] 2.4 Add a runtime artifact materialization path for joined sessions that creates placeholder `agent_def/`, placeholder path artifacts, on-disk `job_dir`, session manifest, session-local `gateway/` artifacts, full tmux env publication (`AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_ID`, `AGENTSYS_AGENT_DEF_DIR`, `AGENTSYS_JOB_DIR`), and shared-registry publication using the long sentinel lease policy.
- [x] 2.5 Add a join-aware construction path for `local_interactive` sessions that adopts an existing pane without launching the provider or applying startup bootstrap.
- [x] 2.6 Wire post-construction control for joined TUI and joined headless sessions so later `state`, `show`, `prompt`, `interrupt`, `turn submit`, and `relaunch` use the normal manifest-first control path.
- [x] 2.7 Align local managed-agent detail and state reporting with adopted tmux window metadata instead of assuming only the launch-time `agent` window naming path.

## 3. Verification and docs

- [x] 3.1 Add unit or integration coverage for successful TUI join, successful headless join with exact resume id, headless join with `--resume-id last`, headless join without `--resume-id`, provider mismatch, missing tmux context, invalid resume selector, long-sentinel-lease publication, and relaunch unavailable vs relaunchable joined sessions.
- [x] 3.2 Add at least one Gemini-specific TUI detection fixture if `gemini_cli` remains supported in v1, or otherwise narrow the supported-provider contract and docs before implementation.
- [x] 3.3 Update `houmao-mgr` operator docs and runtime reference docs to describe `agents join`, its tmux window `0` assumptions, optional headless `--resume-id` semantics, the long-sentinel lease posture, and the joined-session relaunch boundary.
- [x] 3.4 Verify joined sessions remain discoverable through the shared registry and support local `state`, `show`, `prompt`, `interrupt`, `gateway attach`, and headless turn flows as appropriate after adoption.
