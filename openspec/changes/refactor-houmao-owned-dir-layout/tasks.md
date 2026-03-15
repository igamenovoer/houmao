## 1. Shared Path Model

- [ ] 1.1 Add shared Houmao root-resolution helpers for the effective registry, runtime, mailbox, and jobs-root defaults, with tests covering explicit override precedence, env-var override behavior, and default home- or workspace-relative resolution.
- [ ] 1.2 Update runtime-facing CLI and build/start entrypoints, including `src/houmao/agents/realm_controller/cli.py` and `src/houmao/agents/brain_builder.py`, so new Houmao-managed state defaults to `~/.houmao/runtime`, generated homes or manifests use the flat default layout, directory hierarchy no longer depends on tool- or family-grouping buckets, registry-specific `agent_key` is replaced by cross-module `agent_id`, initial `agent_id` bootstrap follows `md5(canonical agent name)` only when no explicit or previously persisted id exists, and any Houmao-owned directory keyed by one agent uses `agent_id` rather than canonical agent name.
- [ ] 1.3 Implement per-agent job-dir derivation at `<working-directory>/.houmao/jobs/<session-id>/` plus the `AGENTSYS_JOB_DIR` session binding in runtime start/resume paths, with focused coverage for tmux-backed and non-CAO session startup.

## 2. Runtime And Registry Layout

- [ ] 2.1 Update runtime session-root consumers such as `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/realm_controller/manifest.py`, and `src/houmao/agents/realm_controller/gateway_storage.py` so the durable runtime-owned session layout remains rooted under the effective Houmao runtime root while the per-agent job dir stays separate, persisted runtime metadata carries canonical agent name plus authoritative `agent_id` plus the actual tmux session name, tmux session naming no longer assumes canonical agent-name uniqueness, and live agent identity is recovered from manifest or shared-registry metadata rather than from the tmux session name itself.
- [ ] 2.2 Keep the shared registry pointer-oriented by updating `src/houmao/agents/realm_controller/registry_models.py`, `src/houmao/agents/realm_controller/registry_storage.py`, related docs, and registry tests so registry publication continues to store discovery metadata only, `agent_id` replaces registry-specific `agent_key`, live-agent directories are keyed by `agent_id`, direct liveness lookup by `agent_id` is supported, convenience lookup by canonical agent name reads registry metadata and can report ambiguity when multiple live agents share one name, warnings are emitted when one `agent_id` is reused with a different canonical name, and launcher, mailbox, or task-local scratch state are not absorbed into the registry.

## 3. CAO Launcher Layout

- [ ] 3.1 Refactor `src/houmao/cao/server_launcher.py` and `src/houmao/cao/tools/cao_server_launcher.py` so launcher artifacts live under `runtime_root/cao_servers/<host>-<port>/launcher/` and the default CAO `HOME` resolves to the sibling `.../home/` path when `home_dir` is omitted.
- [ ] 3.2 Refresh launcher config fixtures, docs, and tests, especially `tests/unit/cao/test_server_launcher.py` and `docs/reference/cao_server_launcher.md`, to cover the new per-server runtime subtree and default-home behavior.

## 4. Mailbox Separation

- [ ] 4.1 Change mailbox default-root resolution in `src/houmao/agents/mailbox_runtime_support.py` and related mailbox bootstrap paths so implicit filesystem mailbox state defaults to `~/.houmao/mailbox`, honors env-var relocation for CI/dynamic runs, and still lets explicit mailbox-root overrides win.
- [ ] 4.2 Update mailbox runtime tests, mailbox transport tests, and agent-facing mailbox skill/reference materials so they describe mailbox as an independent shared writable area rather than a runtime-root-derived subtree.

## 5. Documentation And Verification

- [ ] 5.1 Update runtime, registry, launcher, mailbox, and agent-state reference docs to describe the four-zone ownership model, the env-var override surfaces and precedence rules, the new default Houmao runtime root, the per-agent job dir behavior, the authoritative-`agent_id` model that replaces registry-specific `agent_key`, and the rule that canonical agent name must be learned from manifest or registry metadata rather than inferred from tmux session naming.
- [ ] 5.2 Run focused runtime, launcher, registry, and mailbox test suites plus `openspec validate --strict --json --type change refactor-houmao-owned-dir-layout`.
