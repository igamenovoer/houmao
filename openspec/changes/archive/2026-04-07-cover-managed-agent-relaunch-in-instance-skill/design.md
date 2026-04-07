## Context

`houmao-manage-agent-instance` was introduced as the packaged Houmao-owned skill for live managed-agent lifecycle work, but its original boundary intentionally excluded `agents relaunch`. Since then, the CLI/runtime relaunch surface has become a stable part of the managed-agent lifecycle contract, and the adjacent packaged skills still exclude it as well. The result is a taxonomy gap: the command exists and is documented, but no packaged Houmao-owned skill treats it as a first-class routed action.

This change is narrow. It does not add or redesign relaunch in the CLI/runtime. It only changes which packaged skill owns relaunch guidance and how that skill explains relaunch-specific routing and guardrails.

## Goals / Non-Goals

**Goals:**

- Make `houmao-manage-agent-instance` cover relaunch as part of managed-agent lifecycle guidance.
- Add dedicated relaunch guidance that matches the real `houmao-mgr agents relaunch` contract, including explicit-target and current-session usage.
- Preserve the existing packaged-skill split:
  - instance lifecycle in `houmao-manage-agent-instance`
  - prompt/control in `houmao-agent-messaging`
  - gateway lifecycle in `houmao-agent-gateway`
- Make relaunch failure semantics explicit so packaged guidance does not blur relaunch into fresh launch.

**Non-Goals:**

- No new `houmao-mgr agents relaunch` CLI behavior.
- No runtime recovery redesign for missing tmux sessions or unavailable joined-session relaunch posture.
- No expansion of `houmao-manage-agent-instance` into prompt, interrupt, gateway, mailbox, or turn-management work.
- No change to skill installation sets or auto-install selection.

## Decisions

### 1. Extend the existing lifecycle skill instead of creating a separate relaunch skill

`relaunch` belongs in `houmao-manage-agent-instance` beside launch, join, list, stop, and cleanup.

Why:

- Relaunch acts on one live managed-agent instance and uses the same canonical `agents` lifecycle seam.
- A separate packaged relaunch skill would fragment one small lifecycle family across multiple Houmao-owned entry points.
- The earlier skill design already called out future lifecycle expansion as a likely path, so this is a natural extension rather than a new conceptual split.

Alternative considered:

- Keep relaunch unowned by packaged skills.
- Rejected because it preserves the current taxonomy hole and forces downstream agents to infer routing from raw CLI knowledge instead of from the packaged Houmao skill inventory.

Alternative considered:

- Route relaunch through `houmao-agent-gateway` or `houmao-agent-messaging`.
- Rejected because relaunch is neither gateway lifecycle nor message/control submission. It is managed-instance lifecycle.

### 2. Add one dedicated relaunch action page under the existing skill

The packaged skill should gain a local `actions/relaunch.md` and update the top-level `SKILL.md` workflow to treat relaunch as one of the selected lifecycle actions.

Why:

- The existing skill already uses one-action-per-page structure for launch, join, list, stop, and cleanup.
- Relaunch has distinct target-resolution rules and failure semantics that would be awkward to bury inside launch or stop guidance.
- Adding a dedicated action keeps future lifecycle expansion modular.

Alternative considered:

- Fold relaunch into `actions/launch.md`.
- Rejected because relaunch is not a birth-time creation flow and should not share command-selection rules with new launch.

### 3. Teach both explicit-target and current-session relaunch

The relaunch action should cover:

- `houmao-mgr agents relaunch --agent-name <name>`
- `houmao-mgr agents relaunch --agent-id <id>`
- `houmao-mgr agents relaunch` from inside the owning tmux session when current-session relaunch is intended

Why:

- All three are part of the supported command surface today.
- Omitting current-session relaunch would leave the packaged guidance incomplete for the common “I am already inside the dead/stalled session” workflow.

Alternative considered:

- Support only explicit target selectors in the packaged skill.
- Rejected because the CLI intentionally supports current-session resolution and because current-session relaunch avoids unnecessary target-lookup questions when the agent is already in the owning tmux session.

### 4. Keep relaunch failures explicit and do not silently rewrite them into launch

The packaged guidance should tell agents to report relaunch-unavailable conditions as relaunch failures, not as automatic reasons to run a fresh launch command.

Why:

- Current runtime behavior distinguishes relaunch from new launch. Relaunch preserves the managed-agent home and uses manifest-backed authority; new launch creates a new runtime instance.
- Silent fallback would misrepresent the operator intent and could create a duplicate or semantically different session.
- Fresh launch can still be suggested as a separate next step, but only after the skill reports that relaunch itself is unavailable.

Alternative considered:

- Treat any relaunch failure as implicit permission to run launch instead.
- Rejected because it breaks the lifecycle contract and hides important distinctions such as missing tmux session authority versus missing join-time relaunch posture.

## Risks / Trade-offs

- [The lifecycle skill becomes broader than the original initial cut] → Mitigation: broaden only to `relaunch` and keep prompt, gateway, mailbox, and turn work explicitly out of scope.
- [Agents may overread relaunch as full crash recovery from any state] → Mitigation: make the action page state the current contract clearly, including current-session rules and explicit relaunch-unavailable outcomes.
- [Current-session relaunch can be misapplied outside the owning tmux session] → Mitigation: require explicit target selection when current-session context is unavailable instead of guessing.
- [Skill content and tests may drift if only the top-level page is updated] → Mitigation: update both `SKILL.md` and local action inventory, plus regression coverage that inspects packaged skill content.

## Migration Plan

1. Update the packaged `houmao-manage-agent-instance` top-level skill metadata and workflow to include `relaunch`.
2. Add a dedicated `actions/relaunch.md` page with command shapes, required inputs, and relaunch-specific guardrails.
3. Remove `agents relaunch` from the skill's out-of-scope lists while leaving prompt/gateway/mailbox boundaries unchanged.
4. Update skill-content regression coverage and any docs/references that enumerate the skill's supported lifecycle actions.

## Open Questions

- None for this change. The current proposal intentionally keeps runtime semantics unchanged and only aligns packaged guidance ownership with the existing relaunch contract.
