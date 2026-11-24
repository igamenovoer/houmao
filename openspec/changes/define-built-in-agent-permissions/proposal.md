# Proposal

## Why

Houmao already supports exact grants, but owners have to assemble common roles by hand. An explicit status-only assignment must govern the verified caller's gateway access and delivery to the target's managed inbox. Request, maintenance, and direct-control access need clear, cumulative levels.

## What Changes

- Define six built-in groups. Owners assign the cumulative `agent-observer`, `agent-requester`, `agent-maintainer`, and `agent-operator` roles on one target. `managed-self` receives every supported non-admin effect on its own target. The `agent-admin` group receives every supported client-facing effect under the target's policy.
- Store one `default_permission_group` per target. It starts at `agent-requester` and supplies permissions without enrollment. It sets the access floor for eligible unsigned requests, including requests from a caller whose verified identity has a narrower assignment. Only admins may change the setting, which accepts any of the six built-in groups.
- Let an authorized admin change the retained default while the agent is stopped or its gateway is detached. Provide an explicit owner-local path and a direct passive path where the passive server serves that owner policy.
- Let explicit assignments to the four peer groups replace the default for the verified caller. Add permissions from owner-defined roles, exact-resource templates, and direct grants to the applicable group.
- **BREAKING** Replace the in-memory `managed-self` signer contract with a generation-specific SSH key in the verified execution owner's private `authorization.sqlite3`. The runtime commits the private key and public registration together before startup. Self clients resolve the committed key across headless turns and same-generation process restarts.
- A valid empty admin roster continues to grant open administration within the operation's existing prerequisites. Public health, discovery, and deployment-controlled public input remain an endpoint baseline.
- Complete verified `managed-self` registration before a combined agent-and-gateway launch reports success or advertises the gateway as ready.
- Allow at most one active `managed-self` key per gateway target. After first registration for a runtime generation, changing or revoking that binding requires effective admin authority or proof from the currently registered key.
- Apply Bob's incoming-mail policy before delivery, independently of the agent gateway. Evaluate the verified sender's applicable group and scoped permissions, using the default where eligible. Keep message sending under the sender's mailbox and delegated sending under a separate mailbox permission.
- Let `agent-maintainer` update owner-exposed common plugins of both kinds, skills and MCP, through qualified update providers. Preserve draft isolation, publication attribution, current-base checks, and native readiness rules. Keep exact-resource role templates for skill mounts, mailbox bindings, AG-UI threads, and installed gateway plugin instances.
- Let verified `managed-self` schedule a one-shot publication of a saved candidate for the next qualified idle boundary. Recheck the original authority and expected base before publication.
- Add a work-request input that identifies verified callers or labels unsigned input anonymous. Present both as request content under the target agent's instructions. Authorize verbatim native prompts, supported slash commands, and interruption as distinct effects. Apply the same distinction across gateway, passive, and AG-UI input paths.
- Let the passive server deliver the same wrapped work request to a verified running agent with a detached gateway through a qualified native path. Use the same requester permission and ready-only admission.
- **BREAKING** Replace the broad `agent.prompt` grant with explicit semantics. Existing policies without the setting start with the requester default. Keyed managed mailboxes require an ingress that enforces recipient policy. Include grant migration and mailbox readiness checks in the rollout.

## Capabilities

### New Capabilities

### Modified Capabilities

- `agent-authorization-policy` defines the cumulative role ladder, configurable default and precedence, incoming-mail policy, effect classification, exact-resource templates, and managed runtime registration.
- `authenticated-gateway-access` defines how unsigned default admission and operation-specific proof requirements coexist.
- `brain-launch-runtime` makes verified `managed-self` registration part of launch-time gateway readiness.
- `agent-gateway` distinguishes attributed work requests from direct native controls and exposes the admin-exclusive default-group update.
- `passive-server-gateway-proxy` enforces the input distinction for proxied and direct managed execution, qualifies detached work requests, and provides direct default-group administration for retained targets.
- `per-agent-ag-ui-attachment` uses work-request semantics for thread runs and preserves thread-scoped submission and observation.
- `gateway-versioned-file-edits` defines qualified skills and MCP updates for maintainer and managed-self, including scheduled self-publication, and preserves independent draft and publication rights.
- `houmao-mgr-agents-scope-cli` exposes role catalog and default-group workflows, work requests without recipient enrollment, current-runtime refresh and file access, and scheduled self-publication.
- `houmao-agent-access-skill` teaches assignments, resource templates, and the difference between managed-self, peer, and administrator authority.
- `houmao-agent-files-skill` teaches self-publication at idle and receipt reconciliation.
- `houmao-agent-messaging-skill` routes an ordinary peer work request, direct controls, and email according to their distinct permissions.

## Impact

- PyCasbin authorization and retained policy, SSH proof and runtime signer lifetime, incoming mailbox delivery, gateway request admission, passive relay, AG-UI runs, and versioned common-plugin update providers.
- Scoped manager commands, the existing gateway client and native backend adapters, packaged access and messaging guidance, and operator references for replacing old grants.
- Local execution ownership and passive backing credentials retain their own trust rules. Owners continue to manage custom roles, direct grants, and expiry.
