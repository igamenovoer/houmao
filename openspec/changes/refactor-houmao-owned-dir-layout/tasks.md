## 1. Shared Path Model

- [ ] 1.1 Add shared Houmao root-resolution helpers for the effective registry, runtime, and mailbox defaults, with tests covering default home-relative resolution and existing absolute-path override behavior.
- [ ] 1.2 Update runtime-facing CLI and build/start entrypoints, including `src/houmao/agents/realm_controller/cli.py` and `src/houmao/agents/brain_builder.py`, so new Houmao-managed state defaults to `~/.houmao/runtime` instead of repo-local `tmp/agents-runtime`.
- [ ] 1.3 Implement per-agent job-dir derivation at `<working-directory>/.houmao/jobs/<session-id>/` plus the `AGENTSYS_JOB_DIR` session binding in runtime start/resume paths, with focused coverage for tmux-backed and non-CAO session startup.

## 2. Runtime And Registry Layout

- [ ] 2.1 Update runtime session-root consumers such as `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/realm_controller/manifest.py`, and `src/houmao/agents/realm_controller/gateway_storage.py` so the durable runtime-owned session layout remains rooted under the effective Houmao runtime root while the per-agent job dir stays separate.
- [ ] 2.2 Keep the shared registry pointer-oriented by updating `src/houmao/agents/realm_controller/registry_storage.py`, related docs, and registry tests so registry publication continues to store discovery metadata only and does not absorb launcher, mailbox, or task-local scratch state.

## 3. CAO Launcher Layout

- [ ] 3.1 Refactor `src/houmao/cao/server_launcher.py` and `src/houmao/cao/tools/cao_server_launcher.py` so launcher artifacts live under `runtime_root/cao_servers/<host>-<port>/launcher/` and the default CAO `HOME` resolves to the sibling `.../home/` path when `home_dir` is omitted.
- [ ] 3.2 Refresh launcher config fixtures, docs, and tests, especially `tests/unit/cao/test_server_launcher.py` and `docs/reference/cao_server_launcher.md`, to cover the new per-server runtime subtree and default-home behavior.

## 4. Mailbox Separation

- [ ] 4.1 Change mailbox default-root resolution in `src/houmao/agents/mailbox_runtime_support.py` and related mailbox bootstrap paths so implicit filesystem mailbox state defaults to `~/.houmao/mailbox` while explicit mailbox-root overrides still win.
- [ ] 4.2 Update mailbox runtime tests, mailbox transport tests, and agent-facing mailbox skill/reference materials so they describe mailbox as an independent shared writable area rather than a runtime-root-derived subtree.

## 5. Documentation And Verification

- [ ] 5.1 Update runtime, registry, and agent-state reference docs to describe the four-zone ownership model, including the new default Houmao runtime root and the per-agent job dir under each working directory.
- [ ] 5.2 Run focused runtime, launcher, registry, and mailbox test suites plus `openspec validate --strict --json --type change refactor-houmao-owned-dir-layout`.
