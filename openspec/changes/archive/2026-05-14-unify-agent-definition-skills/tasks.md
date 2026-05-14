## 1. Unified Skill Structure

- [x] 1.1 Refactor `src/houmao/agents/assets/system_skills/houmao-agent-definition/` so `SKILL.md` is a concise router for low-level, easy, ready-profile, and easy-instance lanes.
- [x] 1.2 Add shared subskill/reference pages for launcher resolution, missing-input handling, profile-lane terminology, and credential-routing boundaries.
- [x] 1.3 Move or recreate low-level role and recipe guidance under `houmao-agent-definition/subskills/low-level/`.
- [x] 1.4 Move explicit recipe-backed launch-profile guidance from `houmao-project-mgr` into `houmao-agent-definition/subskills/low-level/launch-profiles.md`.

## 2. Easy Definition Workflows

- [x] 2.1 Move specialist create/set/list/get/remove guidance into `houmao-agent-definition/subskills/easy/specialists.md`.
- [x] 2.2 Move easy-profile create/set/list/get/remove guidance into `houmao-agent-definition/subskills/easy/profiles.md`.
- [x] 2.3 Move easy launch and stop guidance into `houmao-agent-definition/subskills/easy/launch-instance.md` and `stop-instance.md`, preserving handoff to `houmao-agent-instance`.
- [x] 2.4 Move Claude, Codex, and Gemini credential kinds and lookup references under the unified skill and update relative links.

## 3. Ready Profile Workflow

- [x] 3.1 Add `houmao-agent-definition/subskills/easy/create-ready-agent-profile.md`.
- [x] 3.2 Document the ready-profile workflow to create/select a specialist, create/update an easy profile, store supplied launch defaults, and print the launch command without launching.
- [x] 3.3 Include mailbox, gateway, notifier appendix, prompt overlay, memo seed, workdir, model, reasoning, env, and prompt-mode default handling as easy-profile stored defaults.
- [x] 3.4 Add guardrails that avoid manual same-root ordinary mailbox preregistration when easy launch/profile defaults can own launch-time mailbox bootstrap.

## 4. Compatibility And Routing

- [x] 4.1 Replace `houmao-specialist-mgr` with a compatibility wrapper or remove it from current install sets according to the chosen migration decision.
- [x] 4.2 Update `houmao-project-mgr` to route explicit recipe-backed launch-profile authoring to `houmao-agent-definition`.
- [x] 4.3 Update neighboring skill references, including credential, mailbox, workspace, loop, touring, and project-manager routing guidance.
- [x] 4.4 Update project-scope Codex, Claude, and Copilot skill symlinks or copied skill projections if the skill inventory changes.

## 5. Catalog And Docs

- [x] 5.1 Update packaged system-skill catalog and install-set behavior so `houmao-agent-definition` is the canonical pre-launch definition skill.
- [x] 5.2 Update `houmao-mgr system-skills list|install|status|uninstall` expectations and tests for the unified skill and any compatibility wrapper.
- [x] 5.3 Update README system-skill inventory and table rows.
- [x] 5.4 Update getting-started system-skill overview and CLI reference pages.
- [x] 5.5 Update OpenSpec main specs touched by the implementation if archived deltas need follow-up clarification.

## 6. Verification

- [x] 6.1 Run `openspec validate --changes unify-agent-definition-skills`.
- [x] 6.2 Run focused tests for system-skill catalog loading and system-skill install/status behavior.
- [x] 6.3 Run documentation or markdown checks available for the touched docs.
- [x] 6.4 Run `git diff --check`.
