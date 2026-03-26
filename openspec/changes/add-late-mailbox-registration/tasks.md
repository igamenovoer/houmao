## 1. Mailbox Admin CLI

- [ ] 1.1 Add a top-level `houmao-mgr mailbox` command group and wire it into the native CLI tree.
- [ ] 1.2 Implement `houmao-mgr mailbox init` using the filesystem mailbox bootstrap path and shared mailbox-root resolution rules.
- [ ] 1.3 Implement `houmao-mgr mailbox status` with structured filesystem mailbox health and registration summary output.
- [ ] 1.4 Implement `houmao-mgr mailbox register`, `unregister`, and `repair` as local wrappers around the filesystem mailbox lifecycle helpers.

## 2. Managed-Agent Mailbox Registration

- [ ] 2.1 Add `houmao-mgr agents mailbox status|register|unregister` command handlers for local managed-agent targets.
- [ ] 2.2 Extend local managed-agent resolution and validation so late mailbox registration rejects server-backed targets and joined sessions without usable relaunch posture.
- [ ] 2.3 Add runtime-controller helpers to register a filesystem mailbox binding on an existing session, including shared mailbox registration, launch-plan mutation, manifest persistence, and registry refresh.
- [ ] 2.4 Add runtime-controller helpers to unregister a filesystem mailbox binding, including default mailbox deregistration behavior and session unbinding persistence.
- [ ] 2.5 Implement activation-state reporting for `active`, `pending_relaunch`, and `unsupported_joined_session`, and expose it through `agents mailbox status`.

## 3. Verification And Documentation

- [ ] 3.1 Add unit tests for `houmao-mgr mailbox ...` root administration commands and filesystem lifecycle error handling.
- [ ] 3.2 Add unit and integration tests for `houmao-mgr agents mailbox ...` across local headless, local interactive, and joined-session runtime postures.
- [ ] 3.3 Add or update tests covering manifest persistence, registry mailbox summary refresh, and later `agents mail ...` behavior after late registration or unregistration.
- [ ] 3.4 Update CLI and mailbox reference docs to present late mailbox registration as the preferred `houmao-mgr` workflow for local serverless usage.
