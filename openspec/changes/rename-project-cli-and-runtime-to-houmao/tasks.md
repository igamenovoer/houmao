## 1. Packaging And Project Identity

- [ ] 1.1 Update packaging metadata and script entry points so the project/distribution is branded as `Houmao` and the primary runtime CLI is `houmao-cli`, while keeping the `gig_agents` import root and `gig-cao-server` unchanged.
- [ ] 1.2 Update top-level branding and contributor-facing files such as `README.md`, `NOTICE`, docs indexes, and repo guidance files so they present `Houmao` / `houmao-cli` as the canonical project surface.

## 2. Runtime Module Rename

- [ ] 2.1 Rename the runtime source tree from `src/gig_agents/agents/brain_launch_runtime/` to `src/gig_agents/agents/realm_controller/` and update internal importers or module entrypoints that reference the old path.
- [ ] 2.2 Rename the runtime test trees and update direct module-path references across tests, demos, helper scripts, and manual tooling from `brain_launch_runtime` to `realm_controller`.
- [ ] 2.3 Rename runtime reference page filenames and cross-links from `brain_launch_runtime*` to `realm_controller*`, and update linked source-path references in agent, gateway, and mailbox docs.

## 3. Context And OpenSpec Alignment

- [ ] 3.1 Update active `context/` materials excluding `context/logs/` so they use the new project/CLI/runtime names, and rewrite `context/design/namings/` to match the approved narrow scope instead of broader lore-driven renames.
- [ ] 3.2 Update active OpenSpec specs and selected archived/reference OpenSpec text that still teaches the old names, while preserving archive IDs, preserved historical narratives, and log-style provenance where exact history matters.

## 4. Verification

- [ ] 4.1 Run targeted sweeps for `gig-agents`, `gig-agents-cli`, and `brain_launch_runtime` to confirm only approved non-goal or historical exceptions remain.
- [ ] 4.2 Run targeted verification for packaging and runtime surfaces, including CLI/module help checks and relevant Pixi test commands, and refresh generated lock/build metadata when the renamed packaging surface requires it.
