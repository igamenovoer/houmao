## 1. Project Starter Assets And Config Foundations

- [x] 1.1 Add packaged project-starter assets for the local `.houmao/agents/` tree, including canonical directories plus current supported tool adapters and secret-free setup bundles.
- [x] 1.2 Update packaging metadata so the new starter assets ship in built distributions instead of relying on `tests/fixtures/agents/`.
- [x] 1.3 Add project-config models and helpers for `.houmao/houmao-config.toml`, including relative-path resolution from the config directory.

## 2. Project Discovery And Bootstrap CLI

- [x] 2.1 Add the native top-level `houmao-mgr project` command group to the supported CLI tree.
- [x] 2.2 Implement `houmao-mgr project init` so it creates `.houmao/`, writes `.houmao/.gitignore` with the local-only ignore policy, writes `.houmao/houmao-config.toml`, and seeds `.houmao/agents/` without touching the repo root `.gitignore`.
- [x] 2.3 Implement `houmao-mgr project status` so it reports discovered project root, config path, and effective agent-definition root.
- [x] 2.4 Add CLI coverage for `project --help`, fresh init, re-running init on a compatible overlay, and status from both project root and nested subdirectories.

## 3. Project-Aware Default Resolution

- [x] 3.1 Add nearest-ancestor project discovery helpers for `.houmao/houmao-config.toml`.
- [x] 3.2 Update `houmao-mgr brains build` agent-definition-root resolution to consult project discovery after explicit CLI and `AGENTSYS_AGENT_DEF_DIR`, while preserving legacy `.agentsys/agents` fallback.
- [x] 3.3 Update preset-backed native launch resolution to use the same project-aware precedence rules for effective agent-definition-root discovery.
- [x] 3.4 Add unit coverage for explicit override precedence, env-var precedence, ancestor project discovery, and legacy fallback when no project overlay exists.

## 4. Project Credential Commands

- [x] 4.1 Add `houmao-mgr project credential list` and `remove` for tool-scoped auth bundles under `.houmao/agents/tools/<tool>/auth/<name>/`.
- [x] 4.2 Implement `houmao-mgr project credential add claude` so it authors the local Claude auth-bundle layout and required env-backed auth values under the discovered project overlay.
- [x] 4.3 Implement `houmao-mgr project credential add codex` so it authors env-backed Codex auth bundles and optional compatible local auth files under the discovered project overlay.
- [x] 4.4 Implement `houmao-mgr project credential add gemini` so it authors Gemini-compatible local auth bundles under the discovered project overlay.
- [x] 4.5 Add CLI coverage for credential add/list/remove flows, including env-file materialization and optional file projection for supported tools.

## 5. Documentation And Verification

- [x] 5.1 Update repo-level onboarding docs in `README.md` to replace legacy `.agentsys/agents` setup examples with the local `.houmao/` project-init workflow and project credential commands.
- [x] 5.2 Update getting-started docs in `docs/getting-started/quickstart.md` and `docs/getting-started/agent-definitions.md` to describe `houmao-mgr project init`, `.houmao/houmao-config.toml`, `.houmao/.gitignore`, and the local-only `.houmao/agents/` layout instead of manual fixture-copy instructions.
- [x] 5.3 Update CLI reference docs in `docs/reference/cli.md`, `docs/reference/cli/houmao-mgr.md`, and related command pages as needed to document the new `project` command family and the project-aware agent-definition-root discovery order.
- [x] 5.4 Update system-files and operational docs in `docs/reference/system-files/roots-and-ownership.md`, `docs/reference/system-files/operator-preparation.md`, `docs/reference/system-files/agents-and-runtime.md`, `docs/reference/mailbox/quickstart.md`, and related pages as needed to distinguish the repo-local `.houmao/` overlay from per-user `~/.houmao` shared roots and workspace-local job scratch paths.
- [x] 5.5 Refresh examples and contract docs in `docs/reference/houmao_server_pair.md`, `docs/reference/registry/contracts/record-and-layout.md`, `docs/reference/gateway/contracts/protocol-and-state.md`, and adjacent examples that currently embed legacy `.agentsys/agents` paths so samples align with project-local discovery.
- [x] 5.6 Run targeted CLI and resolution test coverage for project init, project discovery, and credential authoring, then confirm the change remains apply-ready.
