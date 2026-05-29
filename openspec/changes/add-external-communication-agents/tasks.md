## 1. External Registry Contract

- [x] 1.1 Add a strict external communication-only registry model with schema version, local name/id, remote pair API base URL, remote agent ref, gateway expectation, lifecycle owner, timestamps, generation id, and cached remote identity.
- [x] 1.2 Add packaged JSON schema coverage for the external registry record and validate records before publish/read.
- [x] 1.3 Extend shared registry path helpers with `external_agents/` while preserving existing `live_agents/` behavior.
- [x] 1.4 Implement external record storage helpers for publish, load by id, resolve by local name, list, verify/update cached identity, and remove.
- [x] 1.5 Add symlink and owned-path safety checks for external record reads/writes/removal consistent with existing registry storage patterns.
- [x] 1.6 Ensure stale local lifecycle cleanup preserves valid external records and does not require external records to have local leases, tmux sessions, or manifest paths.

## 2. External CLI Management

- [x] 2.1 Add `houmao-mgr agents external` command group under the existing agents CLI.
- [x] 2.2 Implement `agents external register --name --api-base-url --agent-ref` with remote passive-server verification, remote identity lookup, gateway expectation flags, collision checks, and explicit replace behavior for existing external records only.
- [x] 2.3 Implement `agents external list` using local registry records without remote polling.
- [x] 2.4 Implement `agents external get` for one local external record with cached identity and remote locator metadata.
- [x] 2.5 Implement `agents external verify` to contact the remote authority, refresh cached identity and verification timestamp, and report gateway availability when expected.
- [x] 2.6 Implement `agents external remove` so it deletes only the local external import and never sends remote lifecycle or gateway detach requests.
- [x] 2.7 Add plain and fancy renderers for external registration, list, get, verify, and remove outputs.

## 3. Target Resolution and Routing

- [x] 3.1 Extend `ManagedAgentTarget` to represent `mode=\"external\"` with pair client, remote agent ref, and external registry record metadata.
- [x] 3.2 Update managed-agent selector resolution so local lifecycle records take precedence, external records resolve next by local id/name, and explicit `--port` bypass remains unchanged.
- [x] 3.3 Add shared helpers for pair-backed targets so existing server and new external targets can reuse safe pair API calls without duplicating logic.
- [x] 3.4 Route external targets through the remote pair API for `agents state`, `prompt`, `interrupt`, `gateway status`, `gateway prompt`, `gateway interrupt`, and supported `agents mail ...` commands.
- [x] 3.5 Add capability gating that rejects external targets for `agents stop`, `agents relaunch`, local cleanup, `gateway attach`, `gateway detach`, `gateway send-keys`, and tmux/current-session selector flows.
- [x] 3.6 Make unsupported-operation errors identify the external local name, remote base URL, remote agent ref, remote lifecycle ownership, and supported communication-safe commands.

## 4. Identity and Presentation

- [x] 4.1 Add optional identity or response metadata needed to distinguish external communication-only targets from local lifecycle targets without replacing the remote transport value.
- [x] 4.2 Update `agents list` aggregation so external records appear from cached identity data without contacting remote authorities.
- [x] 4.3 Update list/state renderers to show local external alias/id, remote lifecycle ownership, remote base URL/ref where appropriate, and no local manifest/tmux fields for external targets.
- [x] 4.4 Ensure remote state failures report the remote connection problem while preserving the local external record.

## 5. Documentation

- [x] 5.1 Update CLI reference docs for `houmao-mgr agents external` register/list/get/verify/remove commands and examples.
- [x] 5.2 Document which normal `houmao-mgr agents` and `agents gateway` commands support external communication-only targets and which commands are rejected.
- [x] 5.3 Add security guidance for remote passive-server exposure through trusted channels such as SSH forwarding, VPN, Tailscale, or secured reverse proxy.
- [x] 5.4 Update registry reference docs with the `external_agents/<external-agent-id>/record.json` layout, schema fields, verification semantics, and cleanup boundaries.
- [x] 5.5 Update filesystem ownership docs to state that external records are registry-owned locator metadata only.

## 6. Tests and Verification

- [x] 6.1 Add unit tests for external registry model validation, schema validation, storage helpers, symlink safety, and remove behavior.
- [x] 6.2 Add CLI tests for external register/list/get/verify/remove using temporary registry roots and fake or local passive-server clients.
- [x] 6.3 Add target-resolution tests for local lifecycle precedence, external id/name resolution, explicit `--port` bypass, and collision handling.
- [x] 6.4 Add routing tests proving external state/prompt/interrupt/gateway/mail commands use the stored remote base URL and remote agent ref without loading local runtime controllers.
- [x] 6.5 Add gating tests proving lifecycle, attach/detach, send-keys, cleanup, and tmux/current-session selector flows fail clearly for external targets.
- [x] 6.6 Run `pixi run lint`, targeted unit tests for the touched modules, and `pixi run test` before marking the change complete.
