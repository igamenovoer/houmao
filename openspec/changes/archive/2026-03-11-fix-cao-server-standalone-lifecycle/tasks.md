## 1. Launcher Standalone Lifecycle

- [x] 1.1 Change `src/gig_agents/cao/server_launcher.py` startup flow so launcher `start` bootstraps `cao-server` as a detached standalone service rather than a parent-lifetime-bound subprocess.
- [x] 1.2 Extend launcher artifacts/result payloads to record standalone-service ownership metadata alongside pid and log paths.
- [x] 1.3 Update launcher `stop` and related verification helpers to manage the detached service safely from later independent command invocations.
- [x] 1.4 Add or update launcher unit/integration coverage to prove that `status` remains healthy after `start` has returned and the original launcher command has exited.

## 2. Interactive Demo Replacement Semantics

- [x] 2.1 Update `src/gig_agents/demo/cao_interactive_demo/cao_server.py` so interactive demo startup always force-replaces the verified fixed-loopback CAO service during agent recreation.
- [x] 2.2 Remove the old confirmation-gated CAO replacement branch from the interactive demo startup flow while keeping explicit failure behavior for unverifiable loopback occupants.
- [x] 2.3 Add or update interactive demo tests to cover deterministic CAO replacement, failure on unverifiable occupants, and no-active-state behavior when replacement fails.

## 3. Demo Pack, Docs, and Expected Reports

- [x] 3.1 Update `scripts/demo/cao-server-launcher/` so the tutorial-pack validates post-start standalone-service survivability and captures any new ownership/report fields.
- [x] 3.2 Refresh expected reports and verification helpers for the launcher demo pack and any interactive demo outputs affected by the new CAO lifecycle contract.
- [x] 3.3 Update relevant docs under `scripts/demo/` and `docs/reference/` to describe detached standalone CAO lifecycle and deterministic replacement during interactive demo startup.
