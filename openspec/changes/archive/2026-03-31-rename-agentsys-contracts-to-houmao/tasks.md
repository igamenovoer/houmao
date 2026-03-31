## 1. Rename shared namespace constants and normalization helpers

- [x] 1.1 Rename the core managed-agent namespace constants in `agent_identity`, `owned_paths`, mailbox runtime helpers, gateway storage/service helpers, CAO no-proxy helpers, and parser preset override constants from `AGENTSYS_*` / `AGENTSYS-` to `HOUMAO_*` / `HOUMAO-`.
- [x] 1.2 Update canonical-name normalization, reserved-prefix validation, tmux session default naming, mailbox principal defaults, and `agent_id` bootstrap hashing so live identities derive from `HOUMAO-<name>`.
- [x] 1.3 Retire the remaining maintained lowercase/internal `agentsys` leftovers such as stale contributor guidance, internal wait-signal strings, and legacy wording in active help or error messages.

## 2. Migrate runtime publication and discovery surfaces

- [x] 2.1 Update runtime session start/resume paths to publish and consume `HOUMAO_MANIFEST_PATH`, `HOUMAO_AGENT_ID`, `HOUMAO_AGENT_DEF_DIR`, `HOUMAO_GATEWAY_*`, `HOUMAO_JOB_DIR`, and related `HOUMAO_*` tmux env vars.
- [x] 2.2 Update shared-root resolution, mailbox transport/runtime bindings, gateway attachability metadata, cleanup current-session targeting, passive-server lookup canonicalization, and project-aware agent-definition precedence to use the renamed `HOUMAO_*` contract.
- [x] 2.3 Rename supported no-proxy and parser-preset override env vars to `HOUMAO_PRESERVE_NO_PROXY_ENV` and `HOUMAO_CAO_CLAUDE_CODE_VERSION`, and update the runtime/CAO integration paths that read them.
- [x] 2.4 Decide and implement the breaking migration posture for already-running sessions and local scripts by removing live reads/writes of the retired `AGENTSYS_*` namespace from supported code paths.

## 3. Refresh supported surfaces and expectations

- [x] 3.1 Update active CLI/help text, runtime docs, getting-started/reference docs, mailbox/gateway/registry docs, and contributor guidance to describe only `HOUMAO-*` identities and `HOUMAO_*` env vars on supported surfaces.
- [x] 3.2 Refresh contract and integration tests, fixture expectations, and example mailbox addresses so they assert `HOUMAO-*` names, `HOUMAO_*` env vars, and the renamed derived hashes where applicable.
- [x] 3.3 Update supported demos and non-archival helper scripts that still export or document `AGENTSYS_*` so active maintained workflows align with the renamed namespace.

## 4. Verify the rename end to end

- [x] 4.1 Run focused runtime, registry, mailbox, gateway, CAO, and passive-server test suites that cover the renamed identity/env contracts.
- [x] 4.2 Run focused grep-based verification over active `src/`, `tests/`, `docs/`, and supported scripts to confirm only archival or intentionally out-of-scope material still contains `AGENTSYS` or lowercase `agentsys`.
- [x] 4.3 Re-run `openspec status --change rename-agentsys-contracts-to-houmao` and confirm the change is apply-ready with proposal, design, specs, and tasks complete.
