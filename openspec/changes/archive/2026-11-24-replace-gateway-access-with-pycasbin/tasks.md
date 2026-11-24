# Tasks

## 1. Policy Model and Retained State

- [x] 1.1 Add the packaged runtime dependency with `pixi add --pypi "pycasbin>=2.8.0,<3"`. Verify `pyproject.toml`, `pixi.lock`, and built wheel metadata include `pycasbin`, and run a PyCasbin import in Pixi.
- [x] 1.2 Implement the fixed domain-scoped evaluator and typed principal, resource, action, grant, and role models. Test exact matching, stable identities, target isolation, role and direct grants, compound checks, and missing or invalid permissions.
- [x] 1.3 Implement owner-private SQLite policy, credential enrollment, role assignment, grant expiry, roster, and audit state. Test offline peer enrollment, revisioned snapshots across processes, unavailability, target ownership, explicit credential rotation, expiry without a policy edit, and retention across gateway reattachment and ordinary relaunch. Document the ownership boundary and state model.
- [x] 1.4 Generate gateway-admin permissions for all supported client-facing actions in the target catalog. Implement the scoped self bundle and the current-decision and handoff interfaces. Test separate ordinary and admin keys on one principal, named and open admin parity, rotation, first and last admin transitions, and revocation of the exact admin qualification before handoff. Document full open admin access.

## 2. SSH Proof and Policy Administration

- [x] 2.1 Replace role-bearing gateway proofs with the versioned SSHSIG caller and bootstrap contracts. Test proposed-key proof, concurrent first enrollment, reuse of a display label or claimed agent ID, request/body/issuer/target/listener binding, replay, invalid proof without anonymous fallback, and retired peer enrollment or managed self generation.
- [x] 2.2 Implement owner-local `agents single access` initialization, principal and credential management, grants, revoke, list, and explain, plus signed first-key and live per-key admin roster commands. Test detached owner workflows, the distinction between removing admin authority and revoking a credential, live rotation that stays keyed, safe explanations, and refusal of general policy edits by a gateway admin.
- [x] 2.3 Add `agents self access public-key` for an owner-selected stable peer signer and keep target selection independent. Test cross-account and offline peer enrollment, signed access after source relaunch, denied proof from a retired key, and enforcement of scope without access to the source runtime. Document peer credential provisioning and key exchange.

## 3. Gateway and Passive Operations

- [x] 3.1 Replace the gateway's route-class inventory with declared semantic operations and resources. Verify startup rejects unclassified core routes and that typed requests distinguish prompt, interruption, raw input, mailbox actions, owner-file access, memory, reminders, and native observation and refresh. Test that both admin modes can use owner-file attachments and a mail-only grant cannot.
- [x] 3.2 Integrate current authority at dispatch, native refresh, deferred work, lifecycle and other protected mutation boundaries. Test revocation after enqueue, optional elevated effects, no effect on denial, and bounded settlement after handoff. Document the gateway decision and error contract.
- [x] 3.3 Apply the same retained policy at passive ingress for direct, detached, and relayed operations. Test canonical target resolution, prompt versus interrupt within a shared downstream route, exact signed and anonymous relay scope, stale or replayed proof, the open epoch across keyed transitions, and detached state and lifecycle. Document forwarded and direct behavior.
- [x] 3.4 Keep one-use backing service authority bound to exact internal operations and preserve direct local manager and executor ownership paths. Test backing restrictions, caller and service provenance, and local owner control with no gateway.

## 4. Browser, Streams, and Plugins

- [x] 4.1 Move browser approval, native ticket issuance and redemption, dashboard guidance, and CLI signer selection to `web.enter`. Test open entry, enrolled callers with and without the action, multiple signing candidates, local-origin restriction, and revocation before redemption. Update Web entry docs and examples.
- [x] 4.2 Authorize AG-UI operations by resolved destination and effect. Recheck output permission on active streams, including a run's output after submission. Test permission revocation with a valid key, destination scoping, detachment without run cancellation, and redacted diagnostics. Update AG-UI wire and user docs.
- [x] 4.3 Replace plugin route class declarations with host-validated actions scoped to the installed instance. Update repository-maintained plugins and test malformed declarations, distinct instances, full named and open admin access, scoped non-admin grants, host status, credential independence, and the built wheel's SDK surface. Document the SDK declaration and grant flow.

## 5. Discovery, Consumers, and Cutover

- [x] 5.1 Replace endpoint and registry authorization descriptors and switch the gateway client, manager commands, bundled skills, demos, and other repository consumers to the new contracts. Test live target verification, secret-free discovery, client refusal of obsolete or mismatched records, and representative CLI flows.
- [x] 5.2 Remove the retired roster, proof, SDK, and route-class loaders and fallbacks. Implement and document explicit owner reprovisioning from a new-schema seed or an intentionally empty roster. Verify an old target fails closed before reprovisioning and that the documented workflow works for a keyed target and for an intentionally open one.
- [x] 5.3 Add explicit per-operator, per-target signing to the local AG-UI workbench. Test local session authorization on signing and host bridge routes, Alice's observe-only key and Bob's run-capable key on separate workbenches, exact signed bytes, verification after reconnect, refusal on unapproved routes or redirects, isolation from upstream executable content, and unsigned open forwarding. Document operator provisioning and credential handling.

## 6. Integrated Verification

- [x] 6.1 Exercise synthetic agents on distinct isolated tmux servers and under separate provisioned OS identities or containers, with inherited `TMUX` and `TMUX_PANE` cleared. Verify enrolled peer proof without shared filesystem access, direct and passive policy, first and last admin transitions, role-only revocation, gateway reattachment, and supported detached operations against the same retained policy.
- [x] 6.2 Run affected unit, integration, and workbench suites, `pixi run lint`, `pixi run typecheck`, `pixi run docs-build`, `pixi run build-dist`, `pixi run check-dist`, and strict OpenSpec validation. Verify the installed wheel starts both maintained entrypoints with the packaged policy engine.
