# Agent Definition Deployment

## Purpose

Resolve one immutable agent-definition revision into project specialist, profile, skills, and launch-ready instance contracts. Planning is read-only with respect to project semantic objects. Apply commits durable project objects and returns a launch handoff; it does not launch the agent.

## Workflow

1. Require an exact validated revision path and explicit values for:
   - deployment, specialist, and profile names;
   - tool and existing credential name;
   - project workdir;
   - every required deploy input;
   - private-workspace selection when the contract is optional;
   - private-workspace workdir and tracking overrides only when the user requests them.
2. Inspect the revision's `deploy-contract.toml` and `instance-contract.toml`. Ask only for missing values. Never derive credentials or secrets from placeholders.
3. Create a plan:

   ```bash
   houmao-mgr project agent-definitions plan <revision> \
     --deployment-name <name> \
     --specialist-name <name> \
     --profile-name <name> \
     --tool <claude|codex|kimi> \
     --credential <existing-name> \
     --workdir <project-path> \
     --set <key>=<value>
   ```

   Add `--private-workspace` or `--no-private-workspace` when the contract permits a choice. Add `--workspace-workdir-mode project-root|private-root` only when requested. Private-workspace tracking starts from the definition contract and can later change through the explicit-target instance-state workspace command.
4. Report the immutable revision digest, instance-contract digest, resolved inputs, selected runtime-state defaults, private-workspace posture, planned artifact digests, and blockers. Planning must leave specialist, profile, skill, and deployment catalog rows unchanged.
5. Apply only after the user accepts the exact plan:

   ```bash
   houmao-mgr project agent-definitions apply <plan.json>
   ```

6. Report registered deployment identity and the explicit `houmao-mgr project agents launch --profile <profile>` handoff. State that no agent was launched.
7. Use maintained lifecycle commands for later work:

   ```bash
   houmao-mgr project agent-definitions inspect [<deployment-name>]
   houmao-mgr project agent-definitions doctor
   houmao-mgr project agent-definitions update <revision> --deployment-name <deployment-name> [plan options]
   houmao-mgr project agent-definitions remove <deployment-name>
   ```

If the request does not map cleanly to this lifecycle, use the native planning tool to build a step-by-step plan from the exact revision, deployment contracts, project state, and user request, then execute the plan.

## Update and Removal

An update must keep the definition identity, target a new immutable revision, use fresh specialist and profile names for recoverable publication, and pass instance-contract compatibility checks for deployed state. Plan it before apply. Removal deletes only resources owned by that deployment and preserves credentials. If live or stored instance state still refers to the deployment, stop and resolve those references first.

## Guardrails

- DO NOT plan from a mutable authoring workspace or a revision with a digest mismatch.
- DO NOT accept unknown deploy keys, invalid typed values, unresolved markers, or context-unsafe rendering.
- DO NOT put secret material in `--set`, plans, journals, revision assets, runtime defaults, or workspace manifests.
- DO NOT apply when the project precondition digest changed after planning; create a new plan.
- DO NOT claim apply launched, prompted, or started any managed-agent instance.
- DO NOT remove shared resources or credential bundles that the deployment does not own.
