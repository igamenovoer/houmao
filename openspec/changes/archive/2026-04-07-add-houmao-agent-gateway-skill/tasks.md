## 1. Packaged Gateway Skill

- [x] 1.1 Create `src/houmao/agents/assets/system_skills/houmao-agent-gateway/` with the top-level `SKILL.md`, tool metadata, and action/reference pages for lifecycle, discovery, gateway-only services, wakeups, and mail-notifier.
- [x] 1.2 Encode the implemented discovery and reminder boundaries in that skill content, including manifest-first current-session targeting, mailbox `resolve-live` for exact `gateway.base_url`, and the non-durable `/v1/wakeups` contract.

## 2. Catalog And Installation

- [x] 2.1 Update the packaged system-skill catalog and any related installer constants so `houmao-agent-gateway` is a current installable skill with its own named set and is included in managed-launch, managed-join, and CLI-default selections.
- [x] 2.2 Update focused catalog, installer, and `houmao-mgr system-skills` CLI tests for the expanded skill inventory and default selection results.

## 3. User-Facing Docs

- [x] 3.1 Update `README.md` so the system-skills overview lists `houmao-agent-gateway` and explains the revised managed auto-install versus CLI-default selection behavior.
- [x] 3.2 Update `docs/reference/cli/system-skills.md` and any related reference text so the lifecycle, messaging, and gateway skill boundaries match the packaged skill set.

## 4. Verification

- [x] 4.1 Run targeted system-skill tests covering catalog loading, installation, and `houmao-mgr system-skills` output.
- [x] 4.2 Sanity-check the new gateway skill content and updated docs against the current gateway contract so they do not describe retired discovery env or unsupported wakeup projections.
